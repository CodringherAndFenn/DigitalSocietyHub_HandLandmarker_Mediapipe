"""
Finger Extension — from a closed fist, extend each finger one at a time in sequence.
index → middle → ring → pinky. One full cycle = one rep.
"""
import time
from .base import BaseExercise
from translations import STRINGS
from tracker.geometry import (
    all_fingers_curled, finger_curl, THRESHOLDS,
    INDEX_TIP, INDEX_MCP,
    MIDDLE_TIP, MIDDLE_MCP,
    RING_TIP, RING_MCP,
    PINKY_TIP, PINKY_MCP,
)

_FINGER_PAIRS = [
    (INDEX_TIP, INDEX_MCP),
    (MIDDLE_TIP, MIDDLE_MCP),
    (RING_TIP, RING_MCP),
    (PINKY_TIP, PINKY_MCP),
]
_FINGER_KEYS = ["index", "middle", "ring", "pinky"]


class FingerExtension(BaseExercise):
    _name_key         = "exercise_finger_ext_name"
    _instructions_key = "exercise_finger_ext_instructions"
    calib_poses = ["open", "fist"]
    injuries = ["finger", "general", "post_surgery"]
    # Same reason as ThumbOpposition: detect_end returns True for one frame only.
    _END_REQUIRED = 1

    def __init__(self):
        super().__init__()
        self._target_idx = 0
        self._sub_cooldown_until = 0.0

    def detect_start(self, lm):
        return all_fingers_curled(lm)

    def detect_end(self, lm):
        now = time.time()
        if now < self._sub_cooldown_until:
            return False

        ext_t = THRESHOLDS['curl_extended']
        curl_t = THRESHOLDS['curl_curled']

        target_tip, target_mcp = _FINGER_PAIRS[self._target_idx]
        target_extended = finger_curl(lm, target_tip, target_mcp) < ext_t
        others_curled = all(
            finger_curl(lm, tip, mcp) > curl_t
            for i, (tip, mcp) in enumerate(_FINGER_PAIRS)
            if i != self._target_idx
        )

        if target_extended and others_curled:
            self._target_idx += 1
            self._sub_cooldown_until = now + 0.4
            if self._target_idx >= len(_FINGER_PAIRS):
                self._target_idx = 0
                return True  # full sequence = one rep
        return False

    def reset(self):
        super().reset()
        self._target_idx = 0
        self._sub_cooldown_until = 0.0

    def feedback_text(self):
        finger = STRINGS[f"finger_{_FINGER_KEYS[self._target_idx]}"]
        return STRINGS["exercise_finger_ext_feedback"].format(finger=finger)
