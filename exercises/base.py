"""
Base exercise class and rep state machine.
All exercises inherit BaseExercise and override detect_start / detect_end.
"""
import time
from collections import deque
from enum import Enum, auto

from translations import STRINGS


class RepState(Enum):
    IDLE = auto()      # waiting for start pose
    AT_START = auto()  # start pose held, watching for end pose
    COOLDOWN = auto()  # brief pause after a rep to prevent double-counting


class BaseExercise:
    """
    Abstract base class for all hand exercises.

    State machine per rep:
        IDLE → (detect_start) → AT_START → (detect_end) → COOLDOWN → IDLE

    If the start pose is lost during AT_START the machine returns to IDLE.
    """
    _name_key: str = "base_name"
    _instructions_key: str = "base_instructions"
    calib_poses: list[str] = []
    injuries: list[str] = []  # tags: "wrist", "finger", "general", "post_surgery"

    @property
    def name(self) -> str:
        return STRINGS[self._name_key]

    @property
    def instructions(self) -> str:
        return STRINGS[self._instructions_key]
    COOLDOWN_SECS: float = 1.5
    _END_WINDOW: int = 5    # frames to look back for end-pose detection
    _END_REQUIRED: int = 3  # minimum True frames in window to fire

    def __init__(self):
        self.state = RepState.IDLE
        self.rep_count = 0
        self.correct_count = 0
        self._state_entered_at: float = 0.0
        self._end_history: deque = deque(maxlen=self._END_WINDOW)

    # ------------------------------------------------------------------
    # Subclass interface
    # ------------------------------------------------------------------

    def detect_start(self, lm: list) -> bool:
        """Return True when the hand is in the exercise start pose."""
        raise NotImplementedError

    def detect_end(self, lm: list) -> bool:
        """Return True when the hand has reached the exercise end pose."""
        raise NotImplementedError

    def validate_correct(self, lm: list) -> bool:
        """
        Optional: return True if the end pose is correctly formed.
        Default always returns True; override for stricter checking.
        """
        return True

    def feedback_text(self) -> str:
        """Optional: return a coaching cue shown during AT_START."""
        return ""

    # ------------------------------------------------------------------
    # Main update — called every frame
    # ------------------------------------------------------------------

    def update(self, lm: list | None) -> dict:
        """
        Process one frame of landmark data.
        Returns a status dict: {state, reps, correct, feedback}
        """
        now = time.time()

        if lm is None:
            self.state = RepState.IDLE
            return self._status(STRINGS["no_hand"])

        if self.state == RepState.IDLE:
            if self.detect_start(lm):
                self.state = RepState.AT_START
                self._state_entered_at = now
                self._end_history.clear()

        elif self.state == RepState.AT_START:
            if not self.detect_start(lm):
                # Lost the start pose before reaching the end
                self.state = RepState.IDLE
                self._end_history.clear()
            else:
                self._end_history.append(self.detect_end(lm))
                if sum(self._end_history) >= self._END_REQUIRED:
                    correct = self.validate_correct(lm)
                    self.rep_count += 1
                    if correct:
                        self.correct_count += 1
                    self.state = RepState.COOLDOWN
                    self._state_entered_at = now
                    self._end_history.clear()

        elif self.state == RepState.COOLDOWN:
            if now - self._state_entered_at >= self.COOLDOWN_SECS:
                self.state = RepState.IDLE

        return self._status(self.feedback_text())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def reset(self):
        self.state = RepState.IDLE
        self.rep_count = 0
        self.correct_count = 0
        self._state_entered_at = 0.0
        self._end_history.clear()

    def _status(self, feedback: str) -> dict:
        return {
            'state': self.state,
            'reps': self.rep_count,
            'correct': self.correct_count,
            'feedback': feedback,
        }
