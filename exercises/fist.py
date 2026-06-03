from .base import BaseExercise
from translations import STRINGS
from tracker.geometry import all_fingers_curled, all_fingers_extended


class FistOpenClose(BaseExercise):
    _name_key         = "exercise_fist_name"
    _instructions_key = "exercise_fist_instructions"
    calib_poses = ["open", "fist"]
    injuries = ["finger", "wrist", "general"]

    def detect_start(self, lm):
        return all_fingers_curled(lm)

    def detect_end(self, lm):
        return all_fingers_extended(lm)

    def feedback_text(self):
        return STRINGS["exercise_fist_feedback"]
