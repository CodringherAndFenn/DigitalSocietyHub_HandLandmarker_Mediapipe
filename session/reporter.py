"""
Session report generation — JSON, CSV, and on-screen summary lines.
"""
import csv
import json
import os
from datetime import datetime, timezone

from session.session import ExerciseLog, Session
from translations import STRINGS


def _session_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_session_json(session: Session, output_dir: str = "sessions") -> str:
    os.makedirs(output_dir, exist_ok=True)
    sid = _session_id()
    filepath = os.path.join(output_dir, f"session_{sid}.json")

    data = {
        "schema_version": "1.0",
        "session_id": sid,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_duration_seconds": round(session.total_duration_seconds, 1),
            "exercises_performed": len(session.logs),
            "total_reps": session.total_reps,
            "total_correct_reps": session.total_correct,
            "overall_accuracy_pct": session.overall_accuracy_pct,
        },
        "exercises": [_log_to_dict(log, i + 1) for i, log in enumerate(session.logs)],
    }

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    return filepath


def save_session_csv(session: Session, output_dir: str = "sessions") -> str:
    os.makedirs(output_dir, exist_ok=True)
    sid = _session_id()
    filepath = os.path.join(output_dir, f"session_{sid}.csv")

    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["exercise_name", "display_name", "duration_seconds",
                         "total_reps", "correct_reps", "accuracy_pct"])
        for log in session.logs:
            writer.writerow([
                log.exercise_name,
                log.display_name,
                round(log.duration_seconds, 1),
                log.total_reps,
                log.correct_reps,
                log.accuracy_pct,
            ])
    return filepath


def save_session(session: Session, output_dir: str = "sessions") -> tuple[str, str]:
    """Save both JSON and CSV. Returns (json_path, csv_path)."""
    return save_session_json(session, output_dir), save_session_csv(session, output_dir)


def build_summary_lines(session: Session) -> list[str]:
    """Return list of strings ready to render on screen."""
    col_ex   = STRINGS["report_col_exercise"]
    col_reps = STRINGS["report_col_reps"]
    col_corr = STRINGS["report_col_correct"]
    col_acc  = STRINGS["report_col_accuracy"]
    total    = STRINGS["report_total"]

    lines = []
    lines.append(STRINGS["report_title"])
    lines.append("")
    lines.append(f"{col_ex:<22} {col_reps:>5} {col_corr:>8} {col_acc:>9}")
    lines.append("-" * 48)
    for log in session.logs:
        lines.append(
            f"{log.display_name:<22} {log.total_reps:>5} "
            f"{log.correct_reps:>8} {log.accuracy_pct:>8.1f}%"
        )
    lines.append("-" * 48)
    lines.append(
        f"{total:<22} {session.total_reps:>5} "
        f"{session.total_correct:>8} {session.overall_accuracy_pct:>8.1f}%"
    )
    mins, secs = divmod(int(session.total_duration_seconds), 60)
    lines.append(STRINGS["report_duration"].format(m=mins, s=secs))
    return lines


def _log_to_dict(log: ExerciseLog, log_number: int) -> dict:
    def iso(ts):
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

    return {
        "exercise_name": log.exercise_name,
        "display_name": log.display_name,
        "start_time": iso(log.start_time),
        "end_time": iso(log.end_time) if log.end_time else None,
        "duration_seconds": round(log.duration_seconds, 1),
        "total_reps": log.total_reps,
        "correct_reps": log.correct_reps,
        "accuracy_pct": log.accuracy_pct,
        "reps": [
            {
                "rep_number": i + 1,
                "timestamp": iso(r.timestamp),
                "correct": r.correct,
            }
            for i, r in enumerate(log.reps)
        ],
    }
