"""
Claw Hand — MCP joints extended, PIP/DIP joints curled (like a claw shape).
Start: open hand. End: claw position.
"""
from .base import BaseExercise
from translations import STRINGS
from tracker.geometry import (
    all_fingers_extended, orientation_sign, hand_scale, angle_at_joint, THRESHOLDS,
    WRIST,
    INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP,
    MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP,
    RING_MCP, RING_PIP, RING_DIP, RING_TIP,
    PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP,
)

_FINGER_JOINTS = [
    (INDEX_MCP,  INDEX_PIP,  INDEX_DIP,  INDEX_TIP),
    (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP),
    (RING_MCP,   RING_PIP,   RING_DIP,   RING_TIP),
    (PINKY_MCP,  PINKY_PIP,  PINKY_DIP,  PINKY_TIP),
]


class ClawHand(BaseExercise):
    _name_key         = "exercise_claw_name"
    _instructions_key = "exercise_claw_instructions"
    calib_poses = ["open", "claw"]
    injuries = ["finger", "general"]

    def detect_start(self, lm):
        return all_fingers_extended(lm)

    def detect_end(self, lm):
        sign = orientation_sign(lm)
        scale = hand_scale(lm)
        pip_threshold = THRESHOLDS['claw_pip_curled']
        mcp_angle_threshold = THRESHOLDS['claw_mcp_angle']

        satisfied = 0
        for mcp, pip, dip, tip in _FINGER_JOINTS:
            # MCP extended: angle at MCP joint (WRIST→MCP→PIP) stays large when
            # knuckle is raised. Fails gracefully even when PIP drops below MCP in 2D.
            mcp_extended = angle_at_joint(lm, WRIST, mcp, pip) > mcp_angle_threshold
            # PIP curled: DIP drops toward palm relative to PIP
            pip_curled = (lm[dip].y - lm[pip].y) * sign > pip_threshold * scale
            if mcp_extended and pip_curled:
                satisfied += 1
        return satisfied >= 3

    def feedback_text(self):
        return STRINGS["exercise_claw_feedback"]
