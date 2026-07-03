"""
Hand Rehab Tracker main entry point.
Wires tracker, exercises, session state, and UI together.
"""
import argparse
import cv2
import os
import sys
import time

# Windows and linux app building respectvely -- >

def _asset(relative_path: str) -> str:
    """Resolve path to a bundled asset, works both in dev and frozen builds."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


def _sessions_dir() -> str:
    """Return sessions output directory next to the executable (or script in dev)."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "sessions")

from tracker.hand_tracker import HandTracker
from tracker.calibration import Calibrator
from exercises.fist import FistOpenClose
from exercises.spread import FingerSpread
from exercises.pinch import Pinch
from exercises.thumb_opposition import ThumbOpposition
from exercises.finger_extension import FingerExtension
from exercises.claw import ClawHand
from exercises.ok_sign import OKSign
from exercises.tabletop import TabletopPosition
from session.session import Session, SessionPhase
from session import reporter
from ui import renderer
from ui.mouse import MouseState
from translations import STRINGS, set_language

# Exercise registry is modular, can just keep adding exercises
EXERCISES = [
    FistOpenClose(),
    FingerSpread(),
    Pinch(),
    ThumbOpposition(),
    FingerExtension(),
    ClawHand(),
    OKSign(),
    TabletopPosition(),
]

# Injury definitio for injury based navigation and ex selection
INJURY_DEFS = [
    ("injury_wrist_forearm", "wrist"),
    ("injury_finger_thumb",  "finger"),
    ("injury_general",       "general"),
    ("injury_post_surgery",  "post_surgery"),
]

# Motivational messages because its easy
_MOTIVATIONAL = [
    (10, "motiv_10"),
    (8,  "motiv_8"),
    (5,  "motiv_5"),
    (3,  "motiv_3"),
    (1,  "motiv_1"),
]


def _motivational_msg(reps: int) -> str:
    for threshold, key in _MOTIVATIONAL:
        if reps >= threshold:
            return STRINGS[key]
    return ""


# Arrow key codes differ by platform, hardcoded them.
# WARNING: on Linux we use waitKey(1) & 0xFF (codes 82/84). Switching to
# waitKeyEx would change the arrow codes to 65362/65364 and silently break this.
if sys.platform == 'win32':
    KEY_UP   = 2490368
    KEY_DOWN = 2621440
else:
    KEY_UP   = 82
    KEY_DOWN = 84
KEY_ESC   = 27
KEY_SPACE = 32
KEY_Q     = ord('q')
KEY_S     = ord('s')
KEY_P     = ord('p')

# Phases rendered on a plain themed canvas — camera is neither decoded nor
# tracked here (wireframe: camera only appears from the calibration screens on)
NO_CAMERA_PHASES = {
    SessionPhase.INJURY_SELECT,
    SessionPhase.MENU,
    SessionPhase.REPORT,
}


def main():
    # use dutch if --lang nl argument is parsed upon startup
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", default="en", choices=["en", "nl"],
                        help="UI language (default: en)")
    args = parser.parse_args()
    set_language(args.lang)

    session = Session()
    calibrator: Calibrator | None = None
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print(STRINGS["error_no_webcam"])
        sys.exit(1)

    # Probe one frame to fix the canvas size so the window never resizes
    # between camera and non-camera screens.
    ret, probe = cap.read()
    if ret:
        canvas_h, canvas_w = probe.shape[:2]
    else:
        canvas_w, canvas_h = 1280, 720

    window = STRINGS["window_title"]
    # GUI_NORMAL suppresses the Qt toolbar so mouse coords map 1:1 to the image
    cv2.namedWindow(window, cv2.WINDOW_AUTOSIZE | cv2.WINDOW_GUI_NORMAL)
    mouse = MouseState()
    cv2.setMouseCallback(window, mouse.callback)
    is_fullscreen = False

    # Badge state (transient feedback text shown after a rep)
    badge_text: str | None = None
    badge_until: float = 0.0
    prev_reps: int = 0
    prev_correct: int = 0

    # Ghost hand landmark snapshot from patient's best rep this exercise
    ghost_lm: list | None = None

    # Report save paths (set once when report is generated)
    report_paths: tuple[str, str] | None = None

    # Scroll state for the two menus (top visible row; geometry comes from
    # the draw functions, which return max_scroll/visible_rows)
    menu_scroll_row = 0
    menu_max_scroll = 0
    menu_visible_rows = 1
    injury_scroll_row = 0
    injury_max_scroll = 0
    injury_visible_rows = 1
    prev_phase: SessionPhase | None = None

    # The menuuuuuuuuuuuuuuuuuuuuu handler
    with HandTracker(_asset('hand_landmarker.task'), num_hands=1) as tracker:
        while True:
            phase = session.phase
            if phase != prev_phase:
                if phase == SessionPhase.MENU:
                    menu_scroll_row = 0
                elif phase == SessionPhase.INJURY_SELECT:
                    injury_scroll_row = 0
                prev_phase = phase

            if phase in NO_CAMERA_PHASES:
                # grab() keeps the camera buffer fresh (no stale burst later)
                # and paces the loop at camera rate without decode/MediaPipe cost
                cap.grab()
                frame = None
                landmarks = None
                active_hand = None
                canvas = renderer.make_canvas(canvas_w, canvas_h)
            else:
                ret, frame = cap.read()
                if not ret:
                    print(STRINGS["error_no_frame"])
                    break
                landmarks = tracker.process_frame(frame)
                active_hand = landmarks[0] if landmarks else None
                # Camera phases draw straight onto the full camera frame —
                # no letterboxing, the feed fills the window
                canvas = frame
            hover = mouse.pos

            # Compute injury-filtered exercise list every frame (O(8), negligible)
            injury_str_key, injury_tag = INJURY_DEFS[session.selected_injury_idx]
            injury_names = [STRINGS[k] for k, _ in INJURY_DEFS]
            active_exercises = [e for e in EXERCISES if injury_tag in e.injuries]
            session.selected_exercise_idx = min(
                session.selected_exercise_idx, len(active_exercises) - 1
            )
            ex = active_exercises[session.selected_exercise_idx]


            # Phase: INJURY_SELECT
            if phase == SessionPhase.INJURY_SELECT:
                hitmap, injury_max_scroll, injury_visible_rows = renderer.draw_injury_menu(
                    canvas, injury_names, session.selected_injury_idx,
                    injury_scroll_row, hover)
                injury_scroll_row = max(0, min(injury_scroll_row, injury_max_scroll))


            # Phase: MENU
            elif phase == SessionPhase.MENU:
                hitmap, menu_max_scroll, menu_visible_rows = renderer.draw_menu(
                    canvas, [e.name for e in active_exercises],
                    session.selected_exercise_idx, menu_scroll_row, hover)
                menu_scroll_row = max(0, min(menu_scroll_row, menu_max_scroll))


            # Phase: CALIB_INTRO (camera starts here)
            elif phase == SessionPhase.CALIB_INTRO:
                renderer.draw_landmarks(frame, landmarks or [])
                hitmap = renderer.draw_calib_intro(frame, hover)


            # Phase: CALIBRATION
            elif phase == SessionPhase.CALIBRATION:
                calibrator.update(active_hand)
                renderer.draw_landmarks(frame, landmarks or [])
                if calibrator.done or calibrator.skipped:
                    hitmap = renderer.draw_calibration_complete(
                        frame, skipped=calibrator.skipped, hover=hover)
                else:
                    pose = calibrator.current_pose
                    hitmap = renderer.draw_calibration(
                        frame,
                        pose_title=pose.title,
                        instruction=pose.instruction,
                        pose_number=calibrator.pose_number,
                        total_poses=calibrator.total_poses,
                        pose_phase=calibrator.pose_phase,
                        sample_progress=calibrator.sample_progress(),
                        hover=hover,
                    )


            # Phase: COUNTDOWN
            elif phase == SessionPhase.COUNTDOWN:
                remaining = session.countdown_remaining()
                renderer.draw_landmarks(frame, landmarks or [])
                hitmap = renderer.draw_countdown(frame, remaining,
                                                 ex.name, ex.instructions, hover)
                if remaining <= 0:
                    ex.reset()
                    prev_reps = 0
                    prev_correct = 0
                    badge_text = None
                    ghost_lm = None
                    session.begin_exercise()


            # Phase: ACTIVE
            elif phase == SessionPhase.ACTIVE:
                status = ex.update(active_hand)
                current_reps = status['reps']

                # New rep detected - compare counts to determine if it was correct
                if current_reps > prev_reps:
                    rep_was_correct = status['correct'] > prev_correct
                    session.record_rep(rep_was_correct)
                    badge_text = STRINGS["badge_good_rep"] if rep_was_correct else STRINGS["badge_try_again"]
                    badge_until = time.time() + 1.5
                    prev_reps = current_reps
                    prev_correct = status['correct']
                    if active_hand is not None:
                        ghost_lm = active_hand  # snapshot for ghost overlay

                now_badge = badge_text if time.time() < badge_until else None

                # Motivational message when exercise has no coaching cue to show
                feedback = status['feedback']
                if not feedback and current_reps > 0:
                    feedback = _motivational_msg(current_reps)

                renderer.draw_landmarks(frame, landmarks or [])
                if ghost_lm is not None:
                    renderer.draw_ghost_hand(frame, ghost_lm)
                hitmap = renderer.draw_exercise_hud(
                    frame,
                    exercise_name=ex.name,
                    reps=status['reps'],
                    correct=status['correct'],
                    feedback=feedback,
                    badge_text=now_badge,
                    hover=hover,
                )

            # Phase: PAUSED
            elif phase == SessionPhase.PAUSED:
                renderer.draw_landmarks(frame, landmarks or [])
                if ghost_lm is not None:
                    renderer.draw_ghost_hand(frame, ghost_lm)
                hitmap = renderer.draw_paused(frame, prev_reps, hover)

            # Phase: REPORT
            elif phase == SessionPhase.REPORT:
                if report_paths is None:
                    report_paths = reporter.save_session(session, _sessions_dir())
                summary = reporter.build_summary_lines(session)
                hitmap = renderer.draw_report(canvas, summary, report_paths[0], hover)

            cv2.imshow(window, canvas)

            # Key handling (see warning above about waitKeyEx on Linux)
            key = cv2.waitKeyEx(1) if sys.platform == 'win32' else cv2.waitKey(1) & 0xFF

            # Mouse handling — chrome actions run directly; everything else is
            # translated into a synthetic key press so one code path handles both
            quit_requested = False
            scroll_clicks = 0  # from scrollbar arrows/track (index = page size)
            for mx, my in mouse.pop_clicks():
                target = hitmap.hit(mx, my)
                if target is None:
                    continue
                name, idx = target
                if name == 'chrome_quit':
                    quit_requested = True
                elif name == 'chrome_max':
                    is_fullscreen = not is_fullscreen
                    try:
                        cv2.setWindowProperty(
                            window, cv2.WND_PROP_FULLSCREEN,
                            cv2.WINDOW_FULLSCREEN if is_fullscreen else cv2.WINDOW_NORMAL)
                    except cv2.error:
                        pass  # some backends (native Wayland) refuse — acceptable
                elif name == 'chrome_min':
                    pass  # decorative — cv2 has no portable iconify API
                elif name == 'key_up':
                    key = KEY_UP
                elif name == 'key_down':
                    key = KEY_DOWN
                elif name == 'key_q':
                    key = KEY_Q
                elif name == 'scroll_up':
                    scroll_clicks += idx or 1
                elif name == 'scroll_down':
                    scroll_clicks -= idx or 1
                elif name in ('key_space', 'confirm'):
                    key = KEY_SPACE
                elif name == 'injury_option':
                    session.selected_injury_idx = idx
                    key = KEY_SPACE
                elif name == 'exercise_option':
                    session.selected_exercise_idx = idx
                    key = KEY_SPACE

            # Wheel + scrollbar clicks (positive = up). NOTE: the Qt HighGUI
            # backend also zooms the view on wheel-up (no API to disable;
            # CTRL+Z resets) — the clickable scrollbar is the zoom-proof path.
            scroll = mouse.pop_scroll() + scroll_clicks

            if quit_requested or key == KEY_ESC:
                break

            elif phase == SessionPhase.INJURY_SELECT:
                n = len(INJURY_DEFS)
                if scroll:
                    injury_scroll_row = max(0, min(injury_scroll_row - scroll,
                                                   injury_max_scroll))
                if key in (KEY_UP, KEY_DOWN):
                    step = -1 if key == KEY_UP else 1
                    session.selected_injury_idx = (session.selected_injury_idx + step) % n
                    # Auto-scroll to keep the selection visible
                    row = session.selected_injury_idx
                    if row < injury_scroll_row:
                        injury_scroll_row = row
                    elif row >= injury_scroll_row + injury_visible_rows:
                        injury_scroll_row = row - injury_visible_rows + 1
                elif key in [ord(str(i)) for i in range(1, n + 1)]:
                    session.selected_injury_idx = key - ord('1')
                elif key == KEY_SPACE:
                    session.injury_confirmed()
                # Q is a no-op at the root screen

            elif phase == SessionPhase.MENU:
                n = len(active_exercises)
                if scroll:
                    menu_scroll_row = max(0, min(menu_scroll_row - scroll, menu_max_scroll))
                if key in (KEY_UP, KEY_DOWN):
                    step = -1 if key == KEY_UP else 1
                    session.selected_exercise_idx = (session.selected_exercise_idx + step) % n
                    # Auto-scroll to keep the selection visible in the grid
                    row = session.selected_exercise_idx // 2
                    if row < menu_scroll_row:
                        menu_scroll_row = row
                    elif row >= menu_scroll_row + menu_visible_rows:
                        menu_scroll_row = row - menu_visible_rows + 1
                elif key in [ord(str(i)) for i in range(1, n + 1)]:
                    session.selected_exercise_idx = key - ord('1')
                elif key == KEY_SPACE:
                    ex = active_exercises[session.selected_exercise_idx]
                    calibrator = Calibrator(ex.calib_poses)
                    session.start_calibration(ex.name, ex.name)
                elif key == KEY_Q:
                    session.back_to_injury_select()

            elif phase == SessionPhase.CALIB_INTRO:
                if key == KEY_SPACE:
                    calibrator.start()
                    session.begin_calibration()
                elif key == KEY_Q:
                    calibrator = None
                    session.back_to_menu()

            elif phase == SessionPhase.CALIBRATION:
                if calibrator.done or calibrator.skipped:
                    if key == KEY_SPACE:
                        session.calibration_complete()
                else:
                    if key == KEY_S:
                        calibrator.skipped = True
                    elif key == KEY_SPACE:
                        calibrator.confirm_pose()
                if key == KEY_Q:
                    # Restart fresh — aborting mid-way is safe, thresholds are
                    # only applied when calibration completes
                    calibrator = Calibrator(ex.calib_poses)
                    session.back_to_calib_intro()

            elif phase == SessionPhase.COUNTDOWN:
                if key == KEY_Q:
                    session.back_to_menu()

            elif phase == SessionPhase.ACTIVE:
                if key in (KEY_SPACE, KEY_Q):
                    session.end_exercise()
                    report_paths = None  # reset so report regenerates
                elif key == KEY_P:
                    session.pause()

            elif phase == SessionPhase.PAUSED:
                if key == KEY_P:
                    session.resume()
                elif key in (KEY_SPACE, KEY_Q):
                    session.end_exercise()
                    report_paths = None

            elif phase == SessionPhase.REPORT:
                if key == KEY_SPACE:
                    report_paths = None
                    session.back_to_menu()
                elif key == KEY_Q:
                    report_paths = None
                    session.back_to_injury_select()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
