from .base import BaseExercise
from translations import STRINGS
from tracker.geometry import (
    all_fingers_extended, tip_distance, finger_curl, THRESHOLDS,
    THUMB_TIP, INDEX_TIP,
    MIDDLE_TIP, MIDDLE_MCP,
    RING_TIP, RING_MCP,
    PINKY_TIP, PINKY_MCP,
)


class OKSign(BaseExercise):
    _name_key         = "exercise_ok_name"
    _instructions_key = "exercise_ok_instructions"
    calib_poses = ["open", "pinch"]
    injuries = ["finger", "general"]

    def detect_start(self, lm):
        return all_fingers_extended(lm)

    def detect_end(self, lm):
        pinch_ok = tip_distance(lm, THUMB_TIP, INDEX_TIP) < THRESHOLDS['pinch_distance']
        ext_t = THRESHOLDS['curl_extended']
        others_extended = all(
            finger_curl(lm, tip, mcp) < ext_t
            for tip, mcp in [
                (MIDDLE_TIP, MIDDLE_MCP),
                (RING_TIP, RING_MCP),
                (PINKY_TIP, PINKY_MCP),
            ]
        )
        return pinch_ok and others_extended

    def feedback_text(self):
        return STRINGS["exercise_ok_feedback"]
