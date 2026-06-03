from .base import BaseExercise
from translations import STRINGS
from tracker.geometry import (
    all_fingers_extended, tip_distance,
    THUMB_TIP, INDEX_TIP, THRESHOLDS,
)


class Pinch(BaseExercise):
    _name_key         = "exercise_pinch_name"
    _instructions_key = "exercise_pinch_instructions"
    calib_poses = ["open", "pinch"]
    injuries = ["finger", "general", "post_surgery"]

    def detect_start(self, lm):
        return all_fingers_extended(lm)

    def detect_end(self, lm):
        return tip_distance(lm, THUMB_TIP, INDEX_TIP) < THRESHOLDS['pinch_distance']

    def feedback_text(self):
        return STRINGS["exercise_pinch_feedback"]
