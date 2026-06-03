"""
Tabletop Position — MCP joints at ~90 degrees, PIP/DIP fully straight.
Like placing your fingers flat on a table with knuckles raised.
"""
from .base import BaseExercise
from translations import STRINGS
from tracker.geometry import (
    all_fingers_extended, angle_at_joint, THRESHOLDS,
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


class TabletopPosition(BaseExercise):
    _name_key         = "exercise_tabletop_name"
    _instructions_key = "exercise_tabletop_instructions"
    calib_poses = ["open", "tabletop"]
    injuries = ["finger", "wrist", "general", "post_surgery"]

    def detect_start(self, lm):
        return all_fingers_extended(lm)

    def detect_end(self, lm):
        mcp_min = THRESHOLDS['tabletop_mcp_min']
        mcp_max = THRESHOLDS['tabletop_mcp_max']
        pip_straight = THRESHOLDS['tabletop_pip_straight']

        satisfied = 0
        for mcp, pip, dip, tip in _FINGER_JOINTS:
            # MCP angle: measured at the MCP joint between wrist and PIP
            mcp_angle = angle_at_joint(lm, WRIST, mcp, pip)
            if not (mcp_min <= mcp_angle <= mcp_max):
                continue
            # PIP and DIP must remain straight
            if angle_at_joint(lm, mcp, pip, dip) < pip_straight:
                continue
            if angle_at_joint(lm, pip, dip, tip) < pip_straight:
                continue
            satisfied += 1
        return satisfied >= 3

    def feedback_text(self):
        return STRINGS["exercise_tabletop_feedback"]
