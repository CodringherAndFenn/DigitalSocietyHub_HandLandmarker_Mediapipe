"""
Thumb Opposition — touch thumb to each fingertip in sequence (index → middle → ring → pinky).
One full cycle counts as one rep.
"""
import time
from .base import BaseExercise, RepState
from translations import STRINGS
from tracker.geometry import (
    all_fingers_extended, tip_distance,
    THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP, THRESHOLDS,
)

_TARGETS = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
_FINGER_KEYS = ["index", "middle", "ring", "pinky"]

_THRESHOLD_KEYS = [
    'pinch_distance',
    'pinch_distance_middle',
    'pinch_distance_ring',
    'pinch_distance_pinky',
]


class ThumbOpposition(BaseExercise):
    _name_key         = "exercise_thumb_opp_name"
    _instructions_key = "exercise_thumb_opp_instructions"
    calib_poses = ["open", "pinch"]
    injuries = ["finger", "general"]
    # detect_end returns True for exactly one frame per rep (when the cycle completes
    # and _target_idx resets). Temporal smoothing (default 3/5) would swallow that
    # single True. Require only 1 so the rep fires immediately.
    _END_REQUIRED = 1

    def __init__(self):
        super().__init__()
        self._target_idx = 0          # which fingertip we're currently aiming for
        self._sub_cooldown_until = 0.0

    def detect_start(self, lm):
        return all_fingers_extended(lm)

    def detect_end(self, lm):
        # Custom cycling logic: each fingertip touch advances the target.
        # When all 4 are touched, return True (one rep complete).
        now = time.time()
        if now < self._sub_cooldown_until:
            return False

        target = _TARGETS[self._target_idx]
        threshold = THRESHOLDS[_THRESHOLD_KEYS[self._target_idx]]
        if tip_distance(lm, THUMB_TIP, target) < threshold:
            self._target_idx += 1
            self._sub_cooldown_until = now + 0.3  # brief pause before next target
            if self._target_idx >= len(_TARGETS):
                self._target_idx = 0
                return True  # full cycle = one rep
        return False

    def reset(self):
        super().reset()
        self._target_idx = 0
        self._sub_cooldown_until = 0.0

    def feedback_text(self):
        finger = STRINGS[f"finger_{_FINGER_KEYS[self._target_idx]}"]
        return STRINGS["exercise_thumb_opp_feedback"].format(finger=finger)
