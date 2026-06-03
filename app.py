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


# Arrow key codes differ by platform, hardcoded them
if sys.platform == 'win32':
    KEY_UP   = 2490368
    KEY_DOWN = 2621440
else:
    KEY_UP   = 82
    KEY_DOWN = 84
KEY_ENTER = 13
KEY_SPACE = 32
KEY_Q     = ord('q')
KEY_S     = ord('s')
KEY_P     = ord('p')


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

    # Badge state (transient feedback text shown after a rep)
    badge_text: str | None = None
    badge_until: float = 0.0
    prev_reps: int = 0
    prev_correct: int = 0

    # Ghost hand landmark snapshot from patient's best rep this exercise
    ghost_lm: list | None = None

    # Report save paths (set once when report is generated)
    report_paths: tuple[str, str] | None = None

    # The menuuuuuuuuuuuuuuuuuuuuu handler
    with HandTracker(_asset('hand_landmarker.task'), num_hands=1) as tracker:
        while True:
            ret, frame = cap.read()
            if not ret:
                print(STRINGS["error_no_frame"])
                break

            landmarks = tracker.process_frame(frame)
            active_hand = landmarks[0] if landmarks else None

            phase = session.phase

            # Compute injury-filtered exercise list every frame (O(8), negligible)
            injury_str_key, injury_tag = INJURY_DEFS[session.selected_injury_idx]
            injury_names = [STRINGS[k] for k, _ in INJURY_DEFS]
            active_exercises = [e for e in EXERCISES if injury_tag in e.injuries]
            session.selected_exercise_idx = min(
                session.selected_exercise_idx, len(active_exercises) - 1
            )
            ex = active_exercises[session.selected_exercise_idx]

            # ------------------------------------------------------------------
            # Phase: INJURY_SELECT
            # ------------------------------------------------------------------
            if phase == SessionPhase.INJURY_SELECT:
                renderer.draw_landmarks(frame, landmarks or [])
                renderer.draw_injury_menu(frame, injury_names, session.selected_injury_idx)

            # ------------------------------------------------------------------
            # Phase: CALIBRATION
            # ------------------------------------------------------------------
            elif phase == SessionPhase.CALIBRATION:
                calibrator.update(active_hand)
                renderer.draw_landmarks(frame, landmarks or [])
                if calibrator.done or calibrator.skipped:
                    renderer.draw_calibration_complete(frame, skipped=calibrator.skipped)
                else:
                    pose = calibrator.current_pose
                    renderer.draw_calibration(
                        frame,
                        pose_title=pose.title,
                        instruction=pose.instruction,
                        pose_number=calibrator.pose_number,
                        total_poses=calibrator.total_poses,
                        pose_phase=calibrator.pose_phase,
                        sample_progress=calibrator.sample_progress(),
                        started=calibrator.started,
                    )

            # ------------------------------------------------------------------
            # Phase: MENU
            # ------------------------------------------------------------------
            elif phase == SessionPhase.MENU:
                renderer.draw_landmarks(frame, landmarks or [])
                renderer.draw_menu(frame, [e.name for e in active_exercises], session.selected_exercise_idx)

            # ------------------------------------------------------------------
            # Phase: COUNTDOWN
            # ------------------------------------------------------------------
            elif phase == SessionPhase.COUNTDOWN:
                remaining = session.countdown_remaining()
                renderer.draw_landmarks(frame, landmarks or [])
                renderer.draw_countdown(frame, remaining, ex.name, ex.instructions)
                if remaining <= 0:
                    ex.reset()
                    prev_reps = 0
                    prev_correct = 0
                    badge_text = None
                    ghost_lm = None
                    session.begin_exercise()

            # ------------------------------------------------------------------
            # Phase: ACTIVE
            # ------------------------------------------------------------------
            elif phase == SessionPhase.ACTIVE:
                status = ex.update(active_hand)
                current_reps = status['reps']

                # New rep detected — compare cumulative counts to determine if it was correct
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
                renderer.draw_exercise_hud(
                    frame,
                    exercise_name=ex.name,
                    reps=status['reps'],
                    correct=status['correct'],
                    feedback=feedback,
                    badge_text=now_badge,
                )

            # ------------------------------------------------------------------
            # Phase: PAUSED
            # ------------------------------------------------------------------
            elif phase == SessionPhase.PAUSED:
                renderer.draw_landmarks(frame, landmarks or [])
                if ghost_lm is not None:
                    renderer.draw_ghost_hand(frame, ghost_lm)
                renderer.draw_paused(frame, prev_reps)

            # ------------------------------------------------------------------
            # Phase: REPORT
            # ------------------------------------------------------------------
            elif phase == SessionPhase.REPORT:
                if report_paths is None:
                    report_paths = reporter.save_session(session, _sessions_dir())
                summary = reporter.build_summary_lines(session)
                renderer.draw_report(frame, summary, report_paths[0])

            cv2.imshow(STRINGS["window_title"], frame)

            # ------------------------------------------------------------------
            # Key handling
            # ------------------------------------------------------------------
            key = cv2.waitKeyEx(1) if sys.platform == 'win32' else cv2.waitKey(1) & 0xFF

            if key == KEY_Q:
                break

            elif phase == SessionPhase.INJURY_SELECT:
                n = len(INJURY_DEFS)
                if key == KEY_UP:
                    session.selected_injury_idx = (session.selected_injury_idx - 1) % n
                elif key == KEY_DOWN:
                    session.selected_injury_idx = (session.selected_injury_idx + 1) % n
                elif key in [ord(str(i)) for i in range(1, n + 1)]:
                    session.selected_injury_idx = key - ord('1')
                elif key == KEY_ENTER:
                    session.injury_confirmed()

            elif phase == SessionPhase.CALIBRATION:
                if calibrator.done or calibrator.skipped:
                    if key == KEY_ENTER:
                        session.calibration_complete()
                else:
                    if key == KEY_S:
                        calibrator.skipped = True
                    elif key == KEY_ENTER:
                        calibrator.start()
                    elif key == KEY_SPACE:
                        calibrator.confirm_pose()

            elif phase == SessionPhase.MENU:
                n = len(active_exercises)
                if key == KEY_UP:
                    session.selected_exercise_idx = (session.selected_exercise_idx - 1) % n
                elif key == KEY_DOWN:
                    session.selected_exercise_idx = (session.selected_exercise_idx + 1) % n
                elif key in [ord(str(i)) for i in range(1, n + 1)]:
                    session.selected_exercise_idx = key - ord('1')
                elif key == KEY_ENTER:
                    calibrator = Calibrator(ex.calib_poses)
                    session.start_calibration(ex.name, ex.name)

            elif phase == SessionPhase.ACTIVE:
                if key == KEY_SPACE:
                    session.end_exercise()
                    report_paths = None  # reset so report regenerates
                elif key == KEY_P:
                    session.pause()

            elif phase == SessionPhase.PAUSED:
                if key == KEY_P:
                    session.resume()

            elif phase == SessionPhase.REPORT:
                if key == KEY_ENTER:
                    report_paths = None
                    session.go_to_menu()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
