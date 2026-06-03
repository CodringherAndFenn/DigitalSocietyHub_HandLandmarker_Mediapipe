from .base import BaseExercise
from translations import STRINGS
from tracker.geometry import (
    all_fingers_extended, tip_distance,
    INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP, THRESHOLDS,
)


class FingerSpread(BaseExercise):
    _name_key         = "exercise_spread_name"
    _instructions_key = "exercise_spread_instructions"
    calib_poses = ["open", "spread"]
    injuries = ["finger", "wrist", "general", "post_surgery"]

    def detect_start(self, lm):
        # Start = fingers extended but NOT yet spread (tips close together)
        if not all_fingers_extended(lm):
            return False
        spread = THRESHOLDS['spread_distance']
        return (
            tip_distance(lm, INDEX_TIP, MIDDLE_TIP) < spread and
            tip_distance(lm, MIDDLE_TIP, RING_TIP) < spread and
            tip_distance(lm, RING_TIP, PINKY_TIP) < spread
        )

    def detect_end(self, lm):
        if not all_fingers_extended(lm):
            return False
        spread = THRESHOLDS['spread_distance']
        return (
            tip_distance(lm, INDEX_TIP, MIDDLE_TIP) > spread and
            tip_distance(lm, MIDDLE_TIP, RING_TIP) > spread and
            tip_distance(lm, RING_TIP, PINKY_TIP) > spread
        )

    def feedback_text(self):
        return STRINGS["exercise_spread_feedback"]
