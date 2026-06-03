"""
All OpenCV drawing operations. Stateless — receives a frame, returns annotated frame.
Text is rendered via PIL (Liberation Sans) for clear, elderly-friendly typography.
"""
import os
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from tracker.hand_tracker import HAND_CONNECTIONS
from translations import STRINGS


def _asset(relative_path: str) -> str:
    """Resolve path to a bundled asset, works both in dev and frozen builds."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    return os.path.join(base, relative_path)


# --- OpenCV colour palette (BGR) ---
C = {
    'landmark':     (0, 255, 0),
    'connection':   (0, 0, 255),
    'panel_bg':     (20, 20, 20),
    'text_primary': (255, 255, 255),
    'text_accent':  (0, 200, 255),
    'text_good':    (80, 255, 80),
    'text_warn':    (0, 165, 255),
    'text_dim':     (160, 160, 160),
    'overlay_bg':   (0, 0, 0),
    'select_bg':    (55, 110, 40),   # dark green highlight row (BGR)
}

# --- PIL colour palette (RGB — reversed from C dict) ---
C_PIL = {
    'text_primary': (255, 255, 255),
    'text_accent':  (255, 200, 0),    # amber
    'text_good':    (80, 255, 80),
    'text_warn':    (255, 165, 0),
    'text_dim':     (160, 160, 160),
    'panel_bg':     (20, 20, 20),
    'select_bg':    (40, 110, 55),    # dark green
}

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


# ---------------------------------------------------------------------------
# Landmark drawing (pure OpenCV — no text)
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
                     C['connection'], 2)
        for lm in hand:
            cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 5, C['landmark'], -1)
    return frame


# ---------------------------------------------------------------------------
# Ghost hand overlay (pure OpenCV — no text)
# ---------------------------------------------------------------------------

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
# INJURY_SELECT phase
# ---------------------------------------------------------------------------

def draw_injury_menu(frame: np.ndarray, injury_names: list[str], selected_idx: int) -> np.ndarray:
    h, w, _ = frame.shape
    panel_w = 380
    row_h = 52
    row_start_y = 110

    # Background panel
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (panel_w, h), C['panel_bg'], -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    # Highlight selected row
    sel_y = row_start_y + selected_idx * row_h - 6
    cv2.rectangle(frame, (5, sel_y), (panel_w - 10, sel_y + row_h - 4),
                  C['select_bg'], -1)

    t = _TextBatch(frame)
    t.put((10, 10), STRINGS["injury_menu_header"],   28, C_PIL['text_accent'], bold=True)
    t.put((10, 52), STRINGS["injury_menu_subtitle"], 18, C_PIL['text_dim'])
    t.put((10, 76), STRINGS["injury_menu_hint"],     14, C_PIL['text_dim'])

    for i, name in enumerate(injury_names):
        y = row_start_y + i * row_h
        color = C_PIL['text_good'] if i == selected_idx else C_PIL['text_primary']
        bold = (i == selected_idx)
        t.put((14, y), f"{i + 1}.  {name}", 22, color, bold=bold)

    hint_y = h - 72
    t.put((10, hint_y),      STRINGS["injury_menu_nav"],     16, C_PIL['text_dim'])
    t.put((10, hint_y + 24), STRINGS["injury_menu_confirm"], 16, C_PIL['text_dim'])
    t.put((10, hint_y + 48), STRINGS["injury_menu_quit"],    16, C_PIL['text_dim'])
    t.flush()
    return frame


# ---------------------------------------------------------------------------
# MENU phase
# ---------------------------------------------------------------------------

def draw_menu(frame: np.ndarray, exercise_names: list[str], selected_idx: int) -> np.ndarray:
    h, w, _ = frame.shape
    panel_w = 380
    row_h = 52
    row_start_y = 90

    # Background panel
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (panel_w, h), C['panel_bg'], -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    # Highlight selected row
    sel_y = row_start_y + selected_idx * row_h - 6
    cv2.rectangle(frame, (5, sel_y), (panel_w - 10, sel_y + row_h - 4),
                  C['select_bg'], -1)

    t = _TextBatch(frame)
    t.put((10, 10), STRINGS["menu_header"],   28, C_PIL['text_accent'], bold=True)
    t.put((10, 52), STRINGS["menu_subtitle"], 18, C_PIL['text_dim'])

    for i, name in enumerate(exercise_names):
        y = row_start_y + i * row_h
        color = C_PIL['text_good'] if i == selected_idx else C_PIL['text_primary']
        bold = (i == selected_idx)
        t.put((14, y), f"{i + 1}.  {name}", 22, color, bold=bold)

    hint_y = h - 72
    t.put((10, hint_y),      STRINGS["menu_nav"],   16, C_PIL['text_dim'])
    t.put((10, hint_y + 24), STRINGS["menu_start"], 16, C_PIL['text_dim'])
    t.put((10, hint_y + 48), STRINGS["menu_quit"],  16, C_PIL['text_dim'])
    t.flush()
    return frame


# ---------------------------------------------------------------------------
# COUNTDOWN phase
# ---------------------------------------------------------------------------

def draw_countdown(frame: np.ndarray, seconds_remaining: float,
                   exercise_name: str, instructions: str) -> np.ndarray:
    h, w, _ = frame.shape

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), C['overlay_bg'], -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    # Exercise name and instructions via PIL
    t = _TextBatch(frame)
    t.put_centered(w // 2, h // 4, exercise_name, 32, C_PIL['text_accent'], bold=True)
    t.put_wrapped(w // 2, h // 4 + 50, instructions, 20, C_PIL['text_primary'], max_px=500)
    t.flush()

    # Large countdown number stays as OpenCV (already giant)
    num = str(max(1, int(seconds_remaining) + 1) if seconds_remaining > 0 else "GO!")
    scale = 5.0 if num == "GO!" else 6.0
    thickness = 6
    (tw, th), _ = cv2.getTextSize(num, FONT, scale, thickness)
    cv2.putText(frame, num,
                (w // 2 - tw // 2, h // 2 + th // 2),
                FONT, scale, C['text_warn'], thickness)

    return frame


# ---------------------------------------------------------------------------
# ACTIVE phase HUD
# ---------------------------------------------------------------------------

def draw_exercise_hud(frame: np.ndarray, exercise_name: str,
                      reps: int, correct: int, feedback: str,
                      badge_text: str | None = None) -> np.ndarray:
    h, w, _ = frame.shape
    bar_h = 80

    # Pre-compute badge geometry so we can draw the green rect before PIL
    badge_bx = badge_by = badge_bw = badge_bh_px = 0
    if badge_text:
        bb = _pil_font(22, bold=True).getbbox(badge_text)
        badge_bw = bb[2] - bb[0]
        badge_bh_px = bb[3] - bb[1]
        badge_bx = w - badge_bw - 30
        badge_by = 14

    # --- All OpenCV drawing first (backgrounds + badge rect) ---
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, bar_h), C['panel_bg'], -1)
    cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

    box_x1, box_y1 = 10, bar_h + 10
    box_x2, box_y2 = 160, bar_h + 160
    rep_overlay = frame.copy()
    cv2.rectangle(rep_overlay, (box_x1, box_y1), (box_x2, box_y2), C['panel_bg'], -1)
    cv2.addWeighted(rep_overlay, 0.75, frame, 0.25, 0, frame)

    overlay2 = frame.copy()
    cv2.rectangle(overlay2, (0, h - bar_h), (w, h), C['panel_bg'], -1)
    cv2.addWeighted(overlay2, 0.8, frame, 0.2, 0, frame)

    if badge_text:
        cv2.rectangle(frame,
                      (badge_bx - 8, badge_by - 4),
                      (badge_bx + badge_bw + 8, badge_by + badge_bh_px + 8),
                      C['text_good'], -1)

    # --- Single PIL batch for all text ---
    if reps:
        accuracy = STRINGS["hud_correct_of"].format(correct=correct, reps=reps)
        acc_pct  = STRINGS["hud_accuracy_pct"].format(pct=round(correct / reps * 100))
    else:
        accuracy = STRINGS["hud_waiting"]
        acc_pct  = ""
    box_cx = (box_x1 + box_x2) // 2

    t = _TextBatch(frame)
    t.put((10, 12), exercise_name, 26, C_PIL['text_accent'], bold=True)
    t.put((10, 48), f"{accuracy}{acc_pct}", 20, C_PIL['text_primary'])
    if badge_text:
        t.put((badge_bx, badge_by), badge_text, 22, C_PIL['panel_bg'], bold=True)
    t.put_centered(box_cx, bar_h + 42, STRINGS["hud_reps_label"], 14, C_PIL['text_dim'])
    t.put_centered(box_cx, bar_h + 108, str(reps), 72, C_PIL['text_primary'], bold=True)
    t.put((10, h - bar_h + 14), feedback, 20, C_PIL['text_primary'])
    t.put((10, h - bar_h + 50), STRINGS["hud_hints"], 16, C_PIL['text_dim'])
    t.flush()

    return frame


# ---------------------------------------------------------------------------
# CALIBRATION phase
# ---------------------------------------------------------------------------

def draw_calibration(frame: np.ndarray, pose_title: str, instruction: str,
                     pose_number: int, total_poses: int,
                     pose_phase, sample_progress: float,
                     started: bool = False) -> np.ndarray:
    from tracker.calibration import PosePhase
    h, w, _ = frame.shape

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), C['overlay_bg'], -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    t = _TextBatch(frame)

    if not started:
        t.put_centered(w // 2, h // 3 - 30, STRINGS["calib_header"], 32,
                       C_PIL['text_accent'], bold=True)
        t.put_wrapped(w // 2, h // 3 + 20,
                      STRINGS["calib_intro"].format(n=total_poses),
                      20, C_PIL['text_primary'], max_px=520)
        t.put_centered(w // 2, h * 2 // 3, STRINGS["calib_begin"], 24,
                       C_PIL['text_good'], bold=True)
        t.put((10, h - 20), STRINGS["calib_skip_hint"], 16, C_PIL['text_dim'])
        t.flush()
        return frame

    # Active calibration header
    t.put_centered(w // 2, 30,
                   STRINGS["calib_progress_header"].format(n=pose_number, total=total_poses),
                   22, C_PIL['text_accent'], bold=True)
    t.put_centered(w // 2, h // 3, pose_title, 32, C_PIL['text_primary'], bold=True)
    t.put_wrapped(w // 2, h // 3 + 50, instruction, 20, C_PIL['text_dim'], max_px=520)

    mid_y = h // 2 + 30
    if pose_phase == PosePhase.READY:
        t.put_centered(w // 2, mid_y, STRINGS["calib_ready_prompt"],
                       22, C_PIL['text_warn'], bold=True)
    elif pose_phase == PosePhase.SAMPLING:
        # Progress bar (OpenCV — flush first, then draw bar)
        t.flush()
        bar_w, bar_h_cv = 420, 26
        bar_x = w // 2 - bar_w // 2
        bar_y = mid_y - bar_h_cv // 2
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h_cv),
                      C['text_dim'], 2)
        fill = int(bar_w * sample_progress)
        if fill > 0:
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill, bar_y + bar_h_cv),
                          C['text_good'], -1)
        t2 = _TextBatch(frame)
        t2.put_centered(w // 2, mid_y + bar_h_cv + 22, STRINGS["calib_measuring"],
                        20, C_PIL['text_primary'])
        t2.put((10, h - 20), STRINGS["calib_ready_hint"], 16, C_PIL['text_dim'])
        t2.flush()
        return frame
    elif pose_phase == PosePhase.CONFIRM:
        t.put_centered(w // 2, mid_y, STRINGS["calib_done"], 36, C_PIL['text_good'], bold=True)

    t.put((10, h - 20), STRINGS["calib_ready_hint"], 16, C_PIL['text_dim'])
    t.flush()
    return frame


def draw_calibration_complete(frame: np.ndarray, skipped: bool = False) -> np.ndarray:
    h, w, _ = frame.shape
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), C['overlay_bg'], -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    msg = STRINGS["calib_skipped"] if skipped else STRINGS["calib_complete"]
    t = _TextBatch(frame)
    t.put_centered(w // 2, h // 2 - 36, msg, 28, C_PIL['text_good'], bold=True)
    t.put_centered(w // 2, h // 2 + 30, STRINGS["calib_continue"], 22, C_PIL['text_primary'])
    t.flush()
    return frame


# ---------------------------------------------------------------------------
# PAUSED phase
# ---------------------------------------------------------------------------

def draw_paused(frame: np.ndarray, current_reps: int) -> np.ndarray:
    """Full-screen pause overlay — shows reps so far and resume instruction."""
    h, w, _ = frame.shape
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), C['overlay_bg'], -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    body_key = "pause_body_one" if current_reps == 1 else "pause_body_many"
    t = _TextBatch(frame)
    t.put_centered(w // 2, h // 3, STRINGS["pause_header"], 40, C_PIL['text_warn'], bold=True)
    t.put_centered(w // 2, h // 3 + 60,
                   STRINGS[body_key].format(n=current_reps),
                   22, C_PIL['text_primary'])
    t.put_centered(w // 2, h * 2 // 3, STRINGS["pause_resume"], 22,
                   C_PIL['text_good'], bold=True)
    t.flush()
    return frame


# ---------------------------------------------------------------------------
# REPORT phase
# ---------------------------------------------------------------------------

def draw_report(frame: np.ndarray, summary_lines: list[str],
                save_path: str | None = None) -> np.ndarray:
    h, w, _ = frame.shape

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), C['overlay_bg'], -1)
    cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

    t = _TextBatch(frame)
    start_y = 50
    line_h = 32
    for i, line in enumerate(summary_lines):
        color = C_PIL['text_accent'] if i == 0 else C_PIL['text_primary']
        bold = (i == 0)
        size = 28 if i == 0 else 20
        t.put_centered(w // 2, start_y + i * line_h, line, size, color, bold=bold)

    if save_path:
        t.put((10, h - 52),
              STRINGS["report_saved"].format(filename=os.path.basename(save_path)),
              16, C_PIL['text_good'])

    t.put((10, h - 24), STRINGS["report_hints"], 18, C_PIL['text_dim'])
    t.flush()
    return frame
