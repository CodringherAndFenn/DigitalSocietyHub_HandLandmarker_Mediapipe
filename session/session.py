"""
Session state machine and data model.
Phases: MENU → CALIBRATION → COUNTDOWN → ACTIVE → REPORT → (MENU or quit)
"""
import time
from dataclasses import dataclass, field
from enum import Enum, auto


class SessionPhase(Enum):
    INJURY_SELECT = auto()
    MENU = auto()
    CALIBRATION = auto()
    COUNTDOWN = auto()
    ACTIVE = auto()
    PAUSED = auto()
    REPORT = auto()


@dataclass
class RepRecord:
    timestamp: float
    correct: bool


@dataclass
class ExerciseLog:
    exercise_name: str
    display_name: str
    start_time: float
    end_time: float | None = None
    reps: list[RepRecord] = field(default_factory=list)

    @property
    def total_reps(self) -> int:
        return len(self.reps)

    @property
    def correct_reps(self) -> int:
        return sum(1 for r in self.reps if r.correct)

    @property
    def duration_seconds(self) -> float:
        end = self.end_time if self.end_time is not None else time.time()
        return end - self.start_time

    @property
    def accuracy_pct(self) -> float:
        if not self.reps:
            return 0.0
        return round(self.correct_reps / self.total_reps * 100, 1)


class Session:
    COUNTDOWN_DURATION = 3.0  # seconds

    def __init__(self):
        self.phase = SessionPhase.INJURY_SELECT
        self.logs: list[ExerciseLog] = []
        self._current_log: ExerciseLog | None = None
        self._countdown_start: float | None = None
        self._pending_exercise_name: str = ""
        self._pending_display_name: str = ""
        self.selected_exercise_idx: int = 0
        self.selected_injury_idx: int = 0

    # ------------------------------------------------------------------
    # Phase transitions
    # ------------------------------------------------------------------

    def injury_confirmed(self):
        """Transition from INJURY_SELECT to MENU, resetting the exercise selection."""
        self.selected_exercise_idx = 0
        self.phase = SessionPhase.MENU

    def start_calibration(self, exercise_name: str, display_name: str):
        """Transition from MENU to CALIBRATION, storing the pending exercise."""
        self._pending_exercise_name = exercise_name
        self._pending_display_name = display_name
        self.phase = SessionPhase.CALIBRATION

    def calibration_complete(self):
        """Transition from CALIBRATION to COUNTDOWN."""
        self._countdown_start = time.time()
        self.phase = SessionPhase.COUNTDOWN

    def start_countdown(self, exercise_name: str, display_name: str):
        """Transition from MENU to COUNTDOWN (skipping calibration)."""
        self._pending_exercise_name = exercise_name
        self._pending_display_name = display_name
        self._countdown_start = time.time()
        self.phase = SessionPhase.COUNTDOWN

    def countdown_remaining(self) -> float:
        """Seconds left in countdown. Returns 0 when expired."""
        if self._countdown_start is None:
            return self.COUNTDOWN_DURATION
        elapsed = time.time() - self._countdown_start
        return max(0.0, self.COUNTDOWN_DURATION - elapsed)

    def begin_exercise(self):
        """Transition from COUNTDOWN to ACTIVE."""
        self._current_log = ExerciseLog(
            exercise_name=self._pending_exercise_name,
            display_name=self._pending_display_name,
            start_time=time.time(),
        )
        self.phase = SessionPhase.ACTIVE

    def record_rep(self, correct: bool):
        """Record a completed rep during ACTIVE phase."""
        if self._current_log is not None:
            self._current_log.reps.append(RepRecord(timestamp=time.time(), correct=correct))

    def pause(self):
        """Pause the active exercise — ACTIVE → PAUSED."""
        self.phase = SessionPhase.PAUSED

    def resume(self):
        """Resume a paused exercise — PAUSED → ACTIVE."""
        self.phase = SessionPhase.ACTIVE

    def end_exercise(self):
        """Finish the active exercise and move to REPORT."""
        if self._current_log is not None:
            self._current_log.end_time = time.time()
            self.logs.append(self._current_log)
            self._current_log = None
        self.phase = SessionPhase.REPORT

    def go_to_menu(self):
        """Return to INJURY_SELECT from REPORT so patient re-selects category each session."""
        self.phase = SessionPhase.INJURY_SELECT

    def new_session(self):
        """Reset all logs and return to MENU."""
        self.logs = []
        self._current_log = None
        self._countdown_start = None
        self.phase = SessionPhase.MENU

    # ------------------------------------------------------------------
    # Summary helpers
    # ------------------------------------------------------------------

    @property
    def total_reps(self) -> int:
        return sum(log.total_reps for log in self.logs)

    @property
    def total_correct(self) -> int:
        return sum(log.correct_reps for log in self.logs)

    @property
    def overall_accuracy_pct(self) -> float:
        if not self.total_reps:
            return 0.0
        return round(self.total_correct / self.total_reps * 100, 1)

    @property
    def total_duration_seconds(self) -> float:
        return sum(log.duration_seconds for log in self.logs)
