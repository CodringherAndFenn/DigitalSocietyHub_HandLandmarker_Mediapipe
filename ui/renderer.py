"""
All drawing operations. Stateless — every screen function receives a drawing
surface (a plain dark canvas for the no-camera menus, or the raw full-size
camera frame for camera phases), draws onto it, and returns a HitMap of
clickable regions.

Look: basic OpenCV styling — dark background, plain rectangles, white/green/
amber text. The Wireframe3 layout (title bar chrome, button stacks, keycap
legends) is kept; only the visual style is plain.

Scaling: everything was designed at 1280x720. Each screen computes a scale
factor from the surface size so layout and fonts hold up at 640x480 → 1080p.

Text is rendered via PIL (Liberation Sans) for clear, elderly-friendly
typography. Because the PIL round-trip overwrites the whole frame, all cv2
geometry must be drawn BEFORE text is flushed — screens queue their text in a
_TextQueue and flush once at the end.
"""
import os
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from tracker.hand_tracker import HAND_CONNECTIONS
from translations import STRINGS
from ui.hitmap import HitMap


def _asset(relative_path: str) -> str:
    """Resolve path to a bundled asset, works both in dev and frozen builds."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    return os.path.join(base, relative_path)


# --- Palette (BGR). THEME_PIL is the RGB mirror, derived automatically. ---
THEME = {
    'app_bg':          (16, 16, 16),      # dark background everywhere
    'titlebar_fill':   (32, 32, 32),
    'outline':         (120, 120, 120),
    'button_fill':     (44, 44, 44),
    'button_hover':    (70, 70, 70),
    'button_selected': (0, 100, 0),       # dark green fill for the selection
    'keycap_fill':     (52, 52, 52),
    'text_main':       (235, 235, 235),   # white
    'text_dim':        (155, 155, 155),
    'text_light':      (245, 245, 245),
    'accent_good':     (0, 200, 0),       # green
    'accent_warn':     (0, 170, 255),     # amber
    'panel_dark':      (16, 16, 16),      # translucent overlays on camera view
    'landmark':        (0, 255, 0),
    'connection':      (0, 0, 255),
}
THEME_PIL = {k: (v[2], v[1], v[0]) for k, v in THEME.items()}

# --- Reference design size; everything scales relative to this ---
_REF_W, _REF_H = 1280, 720
TITLEBAR_H = 48  # at reference scale

# --- Liberation Sans font paths (bundled in fonts/) ---
_FONT_REG  = _asset(os.path.join("fonts", "LiberationSans-Regular.ttf"))
_FONT_BOLD = _asset(os.path.join("fonts", "LiberationSans-Bold.ttf"))
_font_cache: dict[tuple, ImageFont.FreeTypeFont] = {}

FONT = cv2.FONT_HERSHEY_SIMPLEX  # kept for countdown digits only


def _pil_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key not in _font_cache:
        path = _FONT_BOLD if bold else _FONT_REG
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def _ui_scale(surface: np.ndarray) -> float:
    """Scale factor for layout/fonts relative to the 1280x720 design size."""
    h, w = surface.shape[:2]
    return max(0.45, min(w / _REF_W, h / _REF_H))


# ---------------------------------------------------------------------------
# _TextBatch — batches all PIL text ops into one frame round-trip
# ---------------------------------------------------------------------------

class _TextBatch:
    """Draw PIL text onto an OpenCV BGR frame. One conversion in, one out."""

    def __init__(self, frame: np.ndarray):
        self._frame = frame
        self._img = Image.fromarray(frame[:, :, ::-1])   # BGR → RGB
        self._draw = ImageDraw.Draw(self._img)

    def put(self, pos: tuple, text: str, size: int, color: tuple, bold: bool = False):
        self._draw.text(pos, text, font=_pil_font(size, bold), fill=color)

    def put_centered(self, cx: int, cy: int, text: str, size: int,
                     color: tuple, bold: bool = False):
        f = _pil_font(size, bold)
        bb = self._draw.textbbox((0, 0), text, font=f)
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        self._draw.text((cx - w // 2, cy - h // 2), text, font=f, fill=color)

    def put_wrapped(self, cx: int, start_y: int, text: str, size: int,
                    color: tuple, bold: bool = False, max_px: int = 480):
        f = _pil_font(size, bold)
        words = text.split()
        lines, current = [], ""
        for word in words:
            trial = (current + " " + word).strip()
            bb = self._draw.textbbox((0, 0), trial, font=f)
            if bb[2] - bb[0] <= max_px:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        lh = size + 8
        for i, line in enumerate(lines):
            bb = self._draw.textbbox((0, 0), line, font=f)
            w = bb[2] - bb[0]
            self._draw.text((cx - w // 2, start_y + i * lh), line, font=f, fill=color)

    def flush(self):
        self._frame[:] = np.array(self._img)[:, :, ::-1]   # RGB → BGR


class _TextQueue:
    """Deferred text ops — collected while cv2 shapes are still being drawn,
    then rendered in a single PIL round-trip via flush(canvas)."""

    def __init__(self):
        self._ops: list[tuple] = []

    def put(self, pos, text, size, color, bold=False):
        self._ops.append(('put', pos, text, size, color, bold))

    def put_centered(self, cx, cy, text, size, color, bold=False):
        self._ops.append(('put_centered', cx, cy, text, size, color, bold))

    def put_wrapped(self, cx, start_y, text, size, color, bold=False, max_px=480):
        self._ops.append(('put_wrapped', cx, start_y, text, size, color, bold, max_px))

    def flush(self, frame: np.ndarray):
        if not self._ops:
            return
        t = _TextBatch(frame)
        for method, *args in self._ops:
            getattr(t, method)(*args)
        t.flush()
        self._ops = []


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def make_canvas(width: int, height: int) -> np.ndarray:
    return np.full((height, width, 3), THEME['app_bg'], np.uint8)


def _in_rect(pos, rect) -> bool:
    if pos is None:
        return False
    x, y = pos
    x1, y1, x2, y2 = rect
    return x1 <= x <= x2 and y1 <= y <= y2


def _dim_region(canvas, rect, alpha=0.6, color=None):
    """Blend a dark translucent panel over a region (readable text on camera)."""
    x1, y1, x2, y2 = rect
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(canvas.shape[1], x2), min(canvas.shape[0], y2)
    if x2 <= x1 or y2 <= y1:
        return
    roi = canvas[y1:y2, x1:x2]
    overlay = np.full_like(roi, color if color is not None else THEME['panel_dark'])
    cv2.addWeighted(overlay, alpha, roi, 1 - alpha, 0, roi)


def draw_window_chrome(canvas, tq: _TextQueue, hitmap: HitMap, hover=None,
                       overlay: bool = False):
    """Title bar with min/max/quit diamonds and SETTINGS oval.
    overlay=False → opaque bar on a plain canvas (menu screens).
    overlay=True  → translucent bar drawn over the full-frame camera.
    Returns the interior content rect (x1, y1, x2, y2) all screens lay out in."""
    h, w = canvas.shape[:2]
    s = _ui_scale(canvas)
    S = lambda v: max(1, round(v * s))
    tb_bottom = S(TITLEBAR_H)

    if overlay:
        _dim_region(canvas, (0, 0, w, tb_bottom), 0.6)
    else:
        cv2.rectangle(canvas, (0, 0), (w, tb_bottom), THEME['titlebar_fill'], -1)
    cv2.line(canvas, (0, tb_bottom), (w, tb_bottom), THEME['outline'], 1)

    # min/max/quit diamonds (min is decorative — cv2 has no portable iconify)
    dia_cy = tb_bottom // 2
    r_d = S(10)
    for i, name in enumerate(('chrome_min', 'chrome_max', 'chrome_quit')):
        cx = S(30) + i * S(34)
        rect = (cx - r_d - 4, dia_cy - r_d - 4, cx + r_d + 4, dia_cy + r_d + 4)
        pts = np.array([(cx, dia_cy - r_d), (cx + r_d, dia_cy),
                        (cx, dia_cy + r_d), (cx - r_d, dia_cy)], np.int32)
        if name != 'chrome_min' and _in_rect(hover, rect):
            hover_fill = THEME['accent_warn'] if name == 'chrome_quit' else THEME['button_hover']
            cv2.fillPoly(canvas, [pts], hover_fill)
        cv2.polylines(canvas, [pts], True, THEME['outline'], 2)
        hitmap.add(name, rect)

    # SETTINGS oval — decorative placeholder for a future settings screen
    cv2.ellipse(canvas, (w - S(44), dia_cy), (S(24), S(13)), 0, 0, 360,
                THEME['outline'], 2)

    tq.put_centered(w // 2, dia_cy, STRINGS["chrome_title"], max(12, S(19)),
                    THEME_PIL['text_main'], bold=True)
    return (S(14), tb_bottom + S(12), w - S(14), h - S(12))


def _draw_button(canvas, tq: _TextQueue, rect, label, *,
                 selected=False, hover=None, size=22):
    x1, y1, x2, y2 = rect
    if selected:
        fill = THEME['button_selected']
    elif _in_rect(hover, rect):
        fill = THEME['button_hover']
    else:
        fill = THEME['button_fill']
    cv2.rectangle(canvas, (x1, y1), (x2, y2), fill, -1)
    cv2.rectangle(canvas, (x1, y1), (x2, y2),
                  THEME['accent_good'] if selected else THEME['outline'], 2)
    tq.put_centered((x1 + x2) // 2, (y1 + y2) // 2, label, size,
                    THEME_PIL['text_main'], bold=True)


def _draw_scrollbar(canvas, hitmap: HitMap, x1, top, x2, bottom,
                    scroll_row, max_scroll, visible_rows, total_rows, hover=None):
    """Scrollbar with clickable arrow caps and page-jump track regions —
    the mouse-only scroll path (Qt HighGUI zooms on wheel-up, so the wheel
    alone can't be trusted). Registers 'scroll_up' / 'scroll_down' regions."""
    btn_h = x2 - x1  # square arrow caps
    track_top = top + btn_h
    track_bottom = bottom - btn_h
    cx = (x1 + x2) // 2
    a = max(3, (x2 - x1) // 2 - 4)

    for name, (ry1, ry2), up in (('scroll_up', (top, track_top), True),
                                 ('scroll_down', (track_bottom, bottom), False)):
        rect = (x1, ry1, x2, ry2)
        fill = THEME['button_hover'] if _in_rect(hover, rect) else THEME['keycap_fill']
        cv2.rectangle(canvas, (x1, ry1), (x2, ry2), fill, -1)
        cv2.rectangle(canvas, (x1, ry1), (x2, ry2), THEME['outline'], 1)
        my = (ry1 + ry2) // 2
        base = a if up else -a
        pts = np.array([(cx - a, my + base),
                        (cx + a, my + base),
                        (cx, my - base)], np.int32)
        cv2.fillPoly(canvas, [pts], THEME['text_main'])
        hitmap.add(name, rect)

    cv2.rectangle(canvas, (x1, track_top), (x2, track_bottom), THEME['outline'], 1)
    track_h = track_bottom - track_top
    thumb_h = max(24, track_h * visible_rows // max(1, total_rows))
    thumb_y = track_top + (track_h - thumb_h) * scroll_row // max(1, max_scroll)
    # Track above/below the thumb pages one screenful in that direction
    hitmap.add('scroll_up', (x1, track_top, x2, thumb_y), index=visible_rows)
    hitmap.add('scroll_down', (x1, thumb_y + thumb_h, x2, track_bottom), index=visible_rows)
    cv2.rectangle(canvas, (x1 + 2, thumb_y), (x2 - 2, thumb_y + thumb_h),
                  THEME['button_hover'], -1)
    cv2.rectangle(canvas, (x1 + 2, thumb_y), (x2 - 2, thumb_y + thumb_h),
                  THEME['outline'], 1)


def draw_keycap_legend(canvas, tq: _TextQueue, hitmap: HitMap, content_rect,
                       entries, hover=None, header=None) -> int:
    """Row of drawn keycaps with action labels beneath. entries is a list of
    (glyph, label, region_name) — glyph 'UP'/'DOWN' renders an arrow polygon;
    region_name registers the cap as clickable (synthetic key press in app.py).
    Returns the y of the legend's top divider line."""
    s = _ui_scale(canvas)
    S = lambda v: max(1, round(v * s))
    cx1, cy1, cx2, cy2 = content_rect
    cap_h = S(50)
    header_h = S(32) if header else 0
    top = cy2 - (header_h + cap_h + S(24) + S(12))

    cv2.line(canvas, (cx1, top), (cx2, top), THEME['outline'], 1)
    if header:
        tq.put_centered((cx1 + cx2) // 2, top + S(18), header, max(11, S(16)),
                        THEME_PIL['text_main'], bold=True)

    row_y = top + header_h + S(10)
    space_glyph = STRINGS["key_space_label"]
    widths = [S(110) if glyph == space_glyph else cap_h for glyph, _, _ in entries]
    gap = S(30)
    x = (cx1 + cx2) // 2 - (sum(widths) + gap * (len(entries) - 1)) // 2
    for (glyph, label, region), wd in zip(entries, widths):
        rect = (x, row_y, x + wd, row_y + cap_h)
        fill = THEME['button_hover'] if (region and _in_rect(hover, rect)) else THEME['keycap_fill']
        cv2.rectangle(canvas, (x, row_y), (x + wd, row_y + cap_h), fill, -1)
        cv2.rectangle(canvas, (x, row_y), (x + wd, row_y + cap_h), THEME['outline'], 1)
        acx = x + wd // 2
        if glyph in ('UP', 'DOWN'):
            # Arrows as cv2 polygons — avoids font glyph-coverage issues
            y_a, y_b = row_y + cap_h - S(13), row_y + S(13)
            if glyph == 'UP':
                cv2.arrowedLine(canvas, (acx, y_a), (acx, y_b),
                                THEME['text_main'], 2, tipLength=0.5)
            else:
                cv2.arrowedLine(canvas, (acx, y_b), (acx, y_a),
                                THEME['text_main'], 2, tipLength=0.5)
        else:
            tq.put_centered(acx, row_y + cap_h // 2, glyph, max(10, S(15)),
                            THEME_PIL['text_main'], bold=True)
        tq.put_centered(acx, row_y + cap_h + S(12), label, max(10, S(13)),
                        THEME_PIL['text_dim'])
        if region:
            hitmap.add(region, rect)
        x += wd + gap
    return top


def _menu_legend_entries():
    return [
        (STRINGS["key_space_label"], STRINGS["legend_confirm"], "key_space"),
        ("UP",                       STRINGS["legend_up"],      "key_up"),
        ("DOWN",                     STRINGS["legend_down"],    "key_down"),
        ("Q",                        STRINGS["legend_back"],    "key_q"),
    ]


# ---------------------------------------------------------------------------
# Landmark drawing (pure OpenCV — no text; drawn on the raw camera frame)
# ---------------------------------------------------------------------------

def draw_landmarks(frame: np.ndarray, all_hand_landmarks: list) -> np.ndarray:
    """Draw skeleton connections and joint dots for all detected hands."""
    h, w, _ = frame.shape
    for hand in all_hand_landmarks:
        for start_idx, end_idx in HAND_CONNECTIONS:
            s = hand[start_idx]
            e = hand[end_idx]
            cv2.line(frame,
                     (int(s.x * w), int(s.y * h)),
                     (int(e.x * w), int(e.y * h)),
                     THEME['connection'], 2)
        for lm in hand:
            cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 5, THEME['landmark'], -1)
    return frame


def draw_ghost_hand(frame: np.ndarray, landmarks: list, alpha: float = 0.35) -> np.ndarray:
    """Draw a semi-transparent skeleton showing the patient's best-rep target pose."""
    h, w, _ = frame.shape
    overlay = frame.copy()
    ghost_color = (255, 180, 0)  # blue-cyan in BGR
    for start_idx, end_idx in HAND_CONNECTIONS:
        s, e = landmarks[start_idx], landmarks[end_idx]
        cv2.line(overlay,
                 (int(s.x * w), int(s.y * h)),
                 (int(e.x * w), int(e.y * h)),
                 ghost_color, 2)
    for lm in landmarks:
        cv2.circle(overlay, (int(lm.x * w), int(lm.y * h)), 6, ghost_color, 1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    return frame


# ---------------------------------------------------------------------------
# INJURY_SELECT phase — no camera
# ---------------------------------------------------------------------------

def draw_injury_menu(canvas, injury_names: list[str], selected_idx: int,
                     scroll_row: int = 0, hover=None) -> tuple[HitMap, int, int]:
    """Vertical scrollable button list. Returns (hitmap, max_scroll,
    visible_rows) so app.py can clamp the scroll offset."""
    hitmap = HitMap()
    tq = _TextQueue()
    s = _ui_scale(canvas)
    S = lambda v: max(1, round(v * s))
    cx1, cy1, cx2, cy2 = draw_window_chrome(canvas, tq, hitmap, hover)
    mid_x = (cx1 + cx2) // 2

    tq.put_centered(mid_x, cy1 + S(22), STRINGS["injury_heading"], max(13, S(26)),
                    THEME_PIL['text_main'], bold=True)
    tq.put_centered(mid_x, cy1 + S(56), STRINGS["injury_menu_hint"], max(10, S(16)),
                    THEME_PIL['text_dim'])

    legend_top = draw_keycap_legend(canvas, tq, hitmap, (cx1, cy1, cx2, cy2),
                                    _menu_legend_entries(), hover,
                                    header=STRINGS["legend_header"])

    btn_h, gap = S(58), S(18)
    pitch = btn_h + gap
    area_top = cy1 + S(82)
    area_bottom = legend_top - S(14)
    visible_rows = max(1, (area_bottom - area_top + gap) // pitch)
    n = len(injury_names)
    max_scroll = max(0, n - visible_rows)
    scroll_row = max(0, min(scroll_row, max_scroll))

    sb_w = S(22) if max_scroll > 0 else 0
    btn_w = min(S(580), cx2 - cx1 - S(80) - sb_w)
    shown = min(n, visible_rows)
    total = shown * btn_h + (shown - 1) * gap
    top = area_top + max(0, (area_bottom - area_top - total) // 2)
    for i, name in enumerate(injury_names):
        if not (scroll_row <= i < scroll_row + visible_rows):
            continue
        y = top + (i - scroll_row) * pitch
        rect = (mid_x - btn_w // 2, y, mid_x + btn_w // 2, y + btn_h)
        _draw_button(canvas, tq, rect, name, selected=(i == selected_idx),
                     hover=hover, size=max(12, S(22)))
        hitmap.add("injury_option", rect, index=i)

    if max_scroll > 0:
        _draw_scrollbar(canvas, hitmap, cx2 - sb_w, area_top, cx2, area_bottom,
                        scroll_row, max_scroll, visible_rows, n, hover)

    tq.flush(canvas)
    return hitmap, max_scroll, visible_rows


# ---------------------------------------------------------------------------
# MENU phase (exercise selection grid) — no camera
# ---------------------------------------------------------------------------

def draw_menu(canvas, exercise_names: list[str], selected_idx: int,
              scroll_row: int = 0, hover=None) -> tuple[HitMap, int, int]:
    """2-column scrollable grid. Returns (hitmap, max_scroll, visible_rows)
    so app.py can clamp the scroll offset and auto-scroll on arrow keys."""
    hitmap = HitMap()
    tq = _TextQueue()
    s = _ui_scale(canvas)
    S = lambda v: max(1, round(v * s))
    cx1, cy1, cx2, cy2 = draw_window_chrome(canvas, tq, hitmap, hover)
    mid_x = (cx1 + cx2) // 2

    tq.put_centered(mid_x, cy1 + S(22), STRINGS["menu_heading"], max(13, S(26)),
                    THEME_PIL['text_main'], bold=True)

    legend_top = draw_keycap_legend(canvas, tq, hitmap, (cx1, cy1, cx2, cy2),
                                    _menu_legend_entries(), hover,
                                    header=STRINGS["legend_header"])

    grid_top = cy1 + S(58)
    grid_bottom = legend_top - S(14)
    btn_h, gap = S(64), S(14)
    pitch = btn_h + gap
    visible_rows = max(1, (grid_bottom - grid_top + gap) // pitch)
    n = len(exercise_names)
    total_rows = (n + 1) // 2
    max_scroll = max(0, total_rows - visible_rows)
    scroll_row = max(0, min(scroll_row, max_scroll))

    sb_w = S(22) if max_scroll > 0 else 0
    side = S(12)
    col_gap = S(16)
    col_w = (cx2 - cx1 - 2 * side - sb_w - col_gap) // 2
    for i, name in enumerate(exercise_names):
        row, col = divmod(i, 2)
        if not (scroll_row <= row < scroll_row + visible_rows):
            continue
        x = cx1 + side + col * (col_w + col_gap)
        y = grid_top + (row - scroll_row) * pitch
        rect = (x, y, x + col_w, y + btn_h)
        _draw_button(canvas, tq, rect, name, selected=(i == selected_idx),
                     hover=hover, size=max(12, S(22)))
        hitmap.add("exercise_option", rect, index=i)

    if max_scroll > 0:
        _draw_scrollbar(canvas, hitmap, cx2 - sb_w, grid_top, cx2, grid_bottom,
                        scroll_row, max_scroll, visible_rows, total_rows, hover)

    tq.flush(canvas)
    return hitmap, max_scroll, visible_rows


# ---------------------------------------------------------------------------
# CALIB_INTRO phase — camera starts here; drawn on the full camera frame
# ---------------------------------------------------------------------------

def draw_calib_intro(frame, hover=None) -> HitMap:
    hitmap = HitMap()
    tq = _TextQueue()
    s = _ui_scale(frame)
    S = lambda v: max(1, round(v * s))
    h, w = frame.shape[:2]
    draw_window_chrome(frame, tq, hitmap, hover, overlay=True)
    mid_x = w // 2

    panel_h = S(210)
    _dim_region(frame, (0, h - panel_h, w, h), 0.7)
    py = h - panel_h

    tq.put_centered(mid_x, py + S(24), STRINGS["calib_intro_heading"], max(13, S(24)),
                    THEME_PIL['text_main'], bold=True)
    tq.put_wrapped(mid_x, py + S(50), STRINGS["calib_intro_body"], max(11, S(18)),
                   THEME_PIL['text_main'], max_px=w - S(140))
    tq.put_centered(mid_x, h - S(84), STRINGS["calib_skip_hint"], max(10, S(14)),
                    THEME_PIL['text_dim'])

    btn_w = min(S(680), w - S(60))
    rect = (mid_x - btn_w // 2, h - S(64), mid_x + btn_w // 2, h - S(8))
    _draw_button(frame, tq, rect, STRINGS["btn_start_calibration"], hover=hover,
                 size=max(12, S(22)))
    hitmap.add("confirm", rect)

    tq.flush(frame)
    return hitmap


# ---------------------------------------------------------------------------
# CALIBRATION phase — drawn on the full camera frame
# ---------------------------------------------------------------------------

def draw_calibration(frame, pose_title: str, instruction: str,
                     pose_number: int, total_poses: int,
                     pose_phase, sample_progress: float, hover=None) -> HitMap:
    from tracker.calibration import PosePhase
    hitmap = HitMap()
    tq = _TextQueue()
    s = _ui_scale(frame)
    S = lambda v: max(1, round(v * s))
    h, w = frame.shape[:2]
    draw_window_chrome(frame, tq, hitmap, hover, overlay=True)
    mid_x = w // 2

    panel_h = S(208)
    _dim_region(frame, (0, h - panel_h, w, h), 0.7)
    py = h - panel_h

    tq.put_centered(mid_x, py + S(12),
                    STRINGS["calib_progress_header"].format(n=pose_number, total=total_poses),
                    max(10, S(15)), THEME_PIL['text_dim'], bold=True)
    tq.put_centered(mid_x, py + S(40), pose_title, max(13, S(24)),
                    THEME_PIL['text_main'], bold=True)
    tq.put_wrapped(mid_x, py + S(58), instruction, max(10, S(16)),
                   THEME_PIL['text_dim'], max_px=w - S(140))

    act_y1, act_y2 = py + S(112), py + S(158)
    if pose_phase == PosePhase.READY:
        btn_w = min(S(560), w - S(80))
        rect = (mid_x - btn_w // 2, act_y1, mid_x + btn_w // 2, act_y2)
        _draw_button(frame, tq, rect, STRINGS["calib_ready_prompt"], hover=hover,
                     size=max(11, S(19)))
        hitmap.add("confirm", rect)
    elif pose_phase == PosePhase.SAMPLING:
        bar_w = S(420)
        bar_x = mid_x - bar_w // 2
        cv2.rectangle(frame, (bar_x, act_y1 + S(6)), (bar_x + bar_w, act_y2 - S(6)),
                      THEME['outline'], 2)
        fill = int((bar_w - 8) * sample_progress)
        if fill > 4:
            cv2.rectangle(frame, (bar_x + 4, act_y1 + S(10)),
                          (bar_x + 4 + fill, act_y2 - S(10)),
                          THEME['accent_good'], -1)
        tq.put_centered(mid_x, act_y2 + S(8), STRINGS["calib_measuring"], max(10, S(15)),
                        THEME_PIL['text_dim'])
    elif pose_phase == PosePhase.CONFIRM:
        tq.put_centered(mid_x, (act_y1 + act_y2) // 2, STRINGS["calib_done"],
                        max(15, S(30)), THEME_PIL['accent_good'], bold=True)

    tq.put_centered(mid_x, h - S(14), STRINGS["calib_skip_hint"], max(10, S(13)),
                    THEME_PIL['text_dim'])
    tq.flush(frame)
    return hitmap


def draw_calibration_complete(frame, skipped: bool = False, hover=None) -> HitMap:
    hitmap = HitMap()
    tq = _TextQueue()
    s = _ui_scale(frame)
    S = lambda v: max(1, round(v * s))
    h, w = frame.shape[:2]
    draw_window_chrome(frame, tq, hitmap, hover, overlay=True)
    mid_x = w // 2

    panel_h = S(190)
    _dim_region(frame, (0, h - panel_h, w, h), 0.7)
    py = h - panel_h

    msg = STRINGS["calib_skipped"] if skipped else STRINGS["calib_complete"]
    tq.put_centered(mid_x, py + S(20), msg, max(12, S(22)),
                    THEME_PIL['accent_good'], bold=True)
    tq.put_wrapped(mid_x, py + S(44), STRINGS["calib_done_body"], max(10, S(17)),
                   THEME_PIL['text_main'], max_px=w - S(140))

    btn_w = min(S(680), w - S(60))
    rect = (mid_x - btn_w // 2, h - S(64), mid_x + btn_w // 2, h - S(8))
    _draw_button(frame, tq, rect, STRINGS["btn_start_exercise"], hover=hover,
                 size=max(12, S(22)))
    hitmap.add("confirm", rect)

    tq.flush(frame)
    return hitmap


# ---------------------------------------------------------------------------
# COUNTDOWN phase — drawn on the full camera frame
# ---------------------------------------------------------------------------

def draw_countdown(frame, seconds_remaining: float,
                   exercise_name: str, instructions: str, hover=None) -> HitMap:
    hitmap = HitMap()
    tq = _TextQueue()
    s = _ui_scale(frame)
    S = lambda v: max(1, round(v * s))
    h, w = frame.shape[:2]
    cv2.convertScaleAbs(frame, frame, alpha=0.45)
    draw_window_chrome(frame, tq, hitmap, hover, overlay=True)
    mid_x = w // 2
    bar_h = S(TITLEBAR_H)

    tq.put_centered(mid_x, bar_h + S(48), exercise_name, max(15, S(30)),
                    THEME_PIL['text_light'], bold=True)
    tq.put_wrapped(mid_x, bar_h + S(84), instructions, max(11, S(18)),
                   THEME_PIL['text_light'], max_px=w - S(120))

    # Large countdown number stays as OpenCV (already giant)
    num = str(max(1, int(seconds_remaining) + 1) if seconds_remaining > 0 else "GO!")
    scale = (5.0 if num == "GO!" else 6.0) * s
    thickness = max(2, S(6))
    (tw, th), _ = cv2.getTextSize(num, FONT, scale, thickness)
    cv2.putText(frame, num,
                (mid_x - tw // 2, (bar_h + h) // 2 + th // 2),
                FONT, scale, THEME['accent_warn'], thickness)

    tq.flush(frame)
    return hitmap


# ---------------------------------------------------------------------------
# ACTIVE phase HUD — drawn on the full camera frame
# ---------------------------------------------------------------------------

def draw_exercise_hud(frame, exercise_name: str,
                      reps: int, correct: int, feedback: str,
                      badge_text: str | None = None, hover=None) -> HitMap:
    hitmap = HitMap()
    tq = _TextQueue()
    s = _ui_scale(frame)
    S = lambda v: max(1, round(v * s))
    h, w = frame.shape[:2]
    draw_window_chrome(frame, tq, hitmap, hover, overlay=True)
    mid_x = w // 2
    bar_h = S(TITLEBAR_H)

    if reps:
        accuracy = STRINGS["hud_correct_of"].format(correct=correct, reps=reps)
        acc_pct  = STRINGS["hud_accuracy_pct"].format(pct=round(correct / reps * 100))
    else:
        accuracy = STRINGS["hud_waiting"]
        acc_pct  = ""

    # Top info strip under the title bar
    _dim_region(frame, (0, bar_h, w, bar_h + S(64)), 0.65)
    tq.put((S(12), bar_h + S(6)), exercise_name, max(12, S(22)),
           THEME_PIL['text_light'], bold=True)
    tq.put((S(12), bar_h + S(38)), f"{accuracy}{acc_pct}", max(10, S(16)),
           THEME_PIL['text_light'])

    # Rep counter box
    bx1, by1 = S(10), bar_h + S(76)
    bx2, by2 = S(150), bar_h + S(216)
    _dim_region(frame, (bx1, by1, bx2, by2), 0.65)
    box_cx = (bx1 + bx2) // 2
    tq.put_centered(box_cx, by1 + S(24), STRINGS["hud_reps_label"], max(10, S(14)),
                    THEME_PIL['text_light'])
    tq.put_centered(box_cx, by1 + S(88), str(reps), max(24, S(68)),
                    THEME_PIL['text_light'], bold=True)

    # Badge (Good rep! / Try again) — top-right under the title bar
    if badge_text:
        bsize = max(11, S(20))
        bb = _pil_font(bsize, bold=True).getbbox(badge_text)
        bw = bb[2] - bb[0]
        rx2 = w - S(14)
        rx1 = rx2 - bw - S(28)
        cv2.rectangle(frame, (rx1, bar_h + S(76)), (rx2, bar_h + S(116)),
                      THEME['accent_good'], -1)
        tq.put_centered((rx1 + rx2) // 2, bar_h + S(96), badge_text, bsize,
                        THEME_PIL['text_light'], bold=True)

    # Bottom banner — end-exercise button + pause hint
    banner_h = S(96)
    _dim_region(frame, (0, h - banner_h, w, h), 0.7)

    # Feedback / motivational line just above the banner
    if feedback:
        _dim_region(frame, (0, h - banner_h - S(46), w, h - banner_h), 0.65)
        tq.put_centered(mid_x, h - banner_h - S(23), feedback, max(11, S(18)),
                        THEME_PIL['text_light'])

    btn_w = min(S(680), w - S(60))
    rect = (mid_x - btn_w // 2, h - banner_h + S(10), mid_x + btn_w // 2, h - S(34))
    _draw_button(frame, tq, rect, STRINGS["btn_end_exercise"], hover=hover,
                 size=max(11, S(19)))
    hitmap.add("confirm", rect)
    tq.put_centered(mid_x, h - S(16), STRINGS["hud_pause_hint"], max(10, S(14)),
                    THEME_PIL['text_dim'])

    tq.flush(frame)
    return hitmap


# ---------------------------------------------------------------------------
# PAUSED phase — drawn on the full camera frame
# ---------------------------------------------------------------------------

def draw_paused(frame, current_reps: int, hover=None) -> HitMap:
    hitmap = HitMap()
    tq = _TextQueue()
    s = _ui_scale(frame)
    S = lambda v: max(1, round(v * s))
    h, w = frame.shape[:2]
    cv2.convertScaleAbs(frame, frame, alpha=0.35)
    draw_window_chrome(frame, tq, hitmap, hover, overlay=True)
    mid_x = w // 2
    mid_y = (S(TITLEBAR_H) + h) // 2

    body_key = "pause_body_one" if current_reps == 1 else "pause_body_many"
    tq.put_centered(mid_x, mid_y - S(70), STRINGS["pause_header"], max(18, S(40)),
                    THEME_PIL['accent_warn'], bold=True)
    tq.put_centered(mid_x, mid_y - S(10), STRINGS[body_key].format(n=current_reps),
                    max(12, S(22)), THEME_PIL['text_light'])
    tq.put_centered(mid_x, mid_y + S(60), STRINGS["pause_resume"], max(12, S(22)),
                    THEME_PIL['text_light'], bold=True)

    tq.flush(frame)
    return hitmap


# ---------------------------------------------------------------------------
# REPORT phase — no camera
# ---------------------------------------------------------------------------

def draw_report(canvas, summary_lines: list[str], save_path: str | None = None,
                hover=None) -> HitMap:
    hitmap = HitMap()
    tq = _TextQueue()
    s = _ui_scale(canvas)
    S = lambda v: max(1, round(v * s))
    cx1, cy1, cx2, cy2 = draw_window_chrome(canvas, tq, hitmap, hover)
    mid_x = (cx1 + cx2) // 2

    entries = [
        (STRINGS["key_space_label"], STRINGS["legend_new_exercise"], "key_space"),
        ("Q",                        STRINGS["legend_back"],         "key_q"),
    ]
    legend_top = draw_keycap_legend(canvas, tq, hitmap, (cx1, cy1, cx2, cy2),
                                    entries, hover)

    start_y = cy1 + S(18)
    line_h = S(30)
    for i, line in enumerate(summary_lines):
        color = THEME_PIL['text_main']
        bold = (i == 0)
        size = max(13, S(26)) if i == 0 else max(11, S(18))
        tq.put_centered(mid_x, start_y + i * line_h, line, size, color, bold=bold)

    tq.put_centered(mid_x, legend_top - S(52), STRINGS["report_encouragement"],
                    max(11, S(20)), THEME_PIL['accent_good'], bold=True)
    if save_path:
        tq.put_centered(mid_x, legend_top - S(22),
                        STRINGS["report_saved"].format(filename=os.path.basename(save_path)),
                        max(10, S(14)), THEME_PIL['text_dim'])

    tq.flush(canvas)
    return hitmap
