"""
Per-session calibration — guides the user through 6 reference poses,
measures their personal range of motion, and updates THRESHOLDS in-place.
"""
import time
from dataclasses import field
from enum import Enum, auto
from statistics import mean

from translations import STRINGS
from tracker.geometry import (
    THRESHOLDS, FINGER_PAIRS, finger_curl, tip_distance, angle_at_joint,
    orientation_sign, hand_scale,
    WRIST,
    THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP,
    INDEX_MCP, INDEX_PIP, INDEX_DIP,
    MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP,
    RING_MCP, RING_PIP, RING_DIP,
    PINKY_MCP, PINKY_PIP, PINKY_DIP,
)


class PosePhase(Enum):
    READY    = auto()
    SAMPLING = auto()
    CONFIRM  = auto()


class CalibPose:
    def __init__(self, key: str, title_key: str, instruction_key: str):
        self.key = key
        self._title_key = title_key
        self._instruction_key = instruction_key

    @property
    def title(self) -> str:
        return STRINGS[self._title_key]

    @property
    def instruction(self) -> str:
        return STRINGS[self._instruction_key]


POSES: list[CalibPose] = [
    CalibPose("open",     "pose_open_title",       "pose_open_instruction"),
    CalibPose("fist",     "pose_fist_title",       "pose_fist_instruction"),
    CalibPose("spread",   "pose_spread_title",     "pose_spread_instruction"),
    CalibPose("pinch",    "pose_pinch_title",      "pose_pinch_instruction"),
    CalibPose("claw",     "pose_claw_title",       "pose_claw_instruction"),
    CalibPose("tabletop", "pose_tabletop_title",   "pose_tabletop_instruction"),
]

_FINGER_JOINTS = [
    (INDEX_MCP,  INDEX_PIP,  INDEX_DIP),
    (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP),
    (RING_MCP,   RING_PIP,   RING_DIP),
    (PINKY_MCP,  PINKY_PIP,  PINKY_DIP),
]

_SAMPLE_DURATION  = 2.0   # seconds — hold pose while bar fills
_CONFIRM_DURATION = 0.8   # seconds — brief "Done!" flash
_MIN_SAMPLES      = 5     # fall back to defaults if fewer samples collected


class Calibrator:
    """
    Drives the calibration flow.  Call update() every frame; check done/skipped.
    pose_keys: ordered list of pose keys to run (must be a subset of POSES keys).
    """

    def __init__(self, pose_keys: list[str]):
        self.done:    bool = False
        self.skipped: bool = False
        self.started: bool = False

        all_pose_map = {p.key: p for p in POSES}
        self._poses: list[CalibPose] = [all_pose_map[k] for k in pose_keys]

        self._pose_idx:    int        = 0
        self._pose_phase:  PosePhase  = PosePhase.READY
        self._phase_start: float      = 0.0

        # Accumulated samples per pose key (some poses store extra sub-measurements)
        self._samples: dict[str, list[float]] = {k: [] for k in pose_keys}
        if "tabletop" in pose_keys:
            self._samples["tabletop_pip"] = []
        if "claw" in pose_keys:
            self._samples["claw_mcp"] = []

    # ------------------------------------------------------------------
    # Public read-only properties
    # ------------------------------------------------------------------

    @property
    def current_pose(self) -> CalibPose:
        return self._poses[self._pose_idx]

    @property
    def pose_number(self) -> int:
        """1-based index for display."""
        return self._pose_idx + 1

    @property
    def total_poses(self) -> int:
        return len(self._poses)

    @property
    def pose_phase(self) -> PosePhase:
        return self._pose_phase

    def sample_progress(self) -> float:
        """0.0–1.0 fill fraction during SAMPLING phase."""
        elapsed = time.time() - self._phase_start
        return min(1.0, elapsed / _SAMPLE_DURATION)

    # ------------------------------------------------------------------
    # Main update — call every frame
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Called when the user presses Enter on the intro screen."""
        if not self.started and not self.done and not self.skipped:
            self.started = True

    def confirm_pose(self) -> None:
        """Called when the user presses Space in READY phase — begins sampling."""
        if self.started and self._pose_phase == PosePhase.READY:
            self._transition(PosePhase.SAMPLING)

    def update(self, lm) -> None:
        if self.done or self.skipped or not self.started:
            return

        now = time.time()
        elapsed = now - self._phase_start

        if self._pose_phase == PosePhase.READY:
            pass  # waits for confirm_pose() call

        elif self._pose_phase == PosePhase.SAMPLING:
            if lm is not None:
                self._collect_sample(lm)
            if elapsed >= _SAMPLE_DURATION:
                self._transition(PosePhase.CONFIRM)

        elif self._pose_phase == PosePhase.CONFIRM:
            if elapsed >= _CONFIRM_DURATION:
                self._advance_pose()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _transition(self, phase: PosePhase) -> None:
        self._pose_phase = phase
        self._phase_start = time.time()

    def _collect_sample(self, lm) -> None:
        key = self.current_pose.key
        if key in ("open", "fist"):
            # Average curl across index, middle, ring, pinky
            curls = [finger_curl(lm, tip, mcp) for tip, mcp in FINGER_PAIRS]
            self._samples[key].append(mean(curls))
        elif key == "spread":
            # Average tip distance between 3 adjacent fingertip pairs
            adjacent = [
                (INDEX_TIP,  MIDDLE_TIP),
                (MIDDLE_TIP, RING_TIP),
                (RING_TIP,   PINKY_TIP),
            ]
            dists = [tip_distance(lm, a, b) for a, b in adjacent]
            self._samples[key].append(mean(dists))
        elif key == "pinch":
            self._samples[key].append(tip_distance(lm, THUMB_TIP, INDEX_TIP))
        elif key == "claw":
            # Measure PIP curl: normalized y-drop from PIP to DIP for each finger
            sign = orientation_sign(lm)
            scale = hand_scale(lm)
            pip_drops = [
                (lm[dip].y - lm[pip].y) * sign / scale
                for _, pip, dip in _FINGER_JOINTS
            ]
            self._samples["claw"].append(mean(pip_drops))
            # Also measure MCP angle (WRIST→MCP→PIP) so we can calibrate the
            # angle-based MCP-extended check.
            mcp_angles = [angle_at_joint(lm, WRIST, mcp, pip) for mcp, pip, _ in _FINGER_JOINTS]
            self._samples["claw_mcp"].append(mean(mcp_angles))
        elif key == "tabletop":
            # MCP angle: angle at the MCP joint (wrist→mcp→pip)
            mcp_angles = [angle_at_joint(lm, WRIST, mcp, pip) for mcp, pip, _ in _FINGER_JOINTS]
            self._samples["tabletop"].append(mean(mcp_angles))
            # PIP/DIP straightness: angle at PIP (mcp→pip→dip)
            pip_angles = [angle_at_joint(lm, mcp, pip, dip) for mcp, pip, dip in _FINGER_JOINTS]
            self._samples["tabletop_pip"].append(mean(pip_angles))

    def _advance_pose(self) -> None:
        self._pose_idx += 1
        if self._pose_idx >= len(self._poses):
            self._apply_thresholds()
            self.done = True
        else:
            self._transition(PosePhase.READY)

    def _apply_thresholds(self) -> None:
        """Mutate the shared THRESHOLDS dict with calibrated values."""
        open_s        = self._samples.get("open", [])
        fist_s        = self._samples.get("fist", [])
        spread_s      = self._samples.get("spread", [])
        pinch_s       = self._samples.get("pinch", [])
        claw_s        = self._samples.get("claw", [])
        tabletop_mcp  = self._samples.get("tabletop", [])
        tabletop_pip  = self._samples.get("tabletop_pip", [])

        if len(open_s) >= _MIN_SAMPLES:
            open_curl = mean(open_s)
            THRESHOLDS['curl_extended'] = open_curl + 0.05

        if len(fist_s) >= _MIN_SAMPLES:
            fist_curl = mean(fist_s)
            THRESHOLDS['curl_curled'] = max(fist_curl * 0.70, 0.05)

        if len(spread_s) >= _MIN_SAMPLES:
            THRESHOLDS['spread_distance'] = mean(spread_s) * 0.60

        if len(pinch_s) >= _MIN_SAMPLES:
            base = mean(pinch_s)
            # Index is the calibrated finger; further fingers are progressively harder
            # to reach so their thresholds scale up from the measured index distance.
            THRESHOLDS['pinch_distance']        = base * 1.50
            THRESHOLDS['pinch_distance_middle'] = base * 1.65
            THRESHOLDS['pinch_distance_ring']   = base * 1.80
            THRESHOLDS['pinch_distance_pinky']  = base * 1.95

        claw_mcp_s = self._samples.get("claw_mcp", [])

        if len(claw_s) >= _MIN_SAMPLES:
            # Accept 55% of the user's measured PIP drop as the claw threshold
            THRESHOLDS['claw_pip_curled'] = mean(claw_s) * 0.55

        if len(claw_mcp_s) >= _MIN_SAMPLES:
            # MCP must stay at least 75% as extended as measured during the claw pose
            THRESHOLDS['claw_mcp_angle'] = mean(claw_mcp_s) * 0.75

        if len(tabletop_mcp) >= _MIN_SAMPLES:
            mcp_angle = mean(tabletop_mcp)
            THRESHOLDS['tabletop_mcp_min'] = mcp_angle * 0.75
            THRESHOLDS['tabletop_mcp_max'] = min(mcp_angle * 1.30, 145.0)

        if len(tabletop_pip) >= _MIN_SAMPLES:
            # PIP must stay straighter than 85% of the user's measured straight-finger angle
            THRESHOLDS['tabletop_pip_straight'] = mean(tabletop_pip) * 0.85
