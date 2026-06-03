# Landmarker — Hand Rehabilitation Tracker

A real-time hand rehabilitation exercise tracker that uses your webcam and Google's MediaPipe to detect hand landmarks, count exercise reps, and generate session reports for patients and clinicians.

Designed with rehab patients in mind — the system is intentionally lenient, encourages progress, and never penalises incomplete range of motion.

---

## What it does

- Detects your hand through a standard webcam using MediaPipe's hand landmark model
- Guides you through a calibration phase tailored to your current range of motion
- Counts repetitions for 8 rehabilitation exercises
- Shows a **ghost hand overlay** of your last rep as a visual target
- Saves a **JSON + CSV session report** after every exercise for clinicians to track compliance and improvement over time
- Supports English and Dutch (`--lang nl`)

---

## Exercises

| Exercise | What you do |
|---|---|
| Fist Open / Close | Open from a closed fist |
| Finger Spread | Spread fingers apart from a neutral position |
| Pinch | Bring thumb to index fingertip |
| Thumb Opposition | Touch thumb to each finger in sequence (4 = 1 rep) |
| Finger Extension | Extend each finger from a fist in sequence (4 = 1 rep) |
| Claw Hand | Curl PIP/DIP joints while keeping MCP joints raised |
| OK Sign | Form an OK shape with thumb and index, other fingers straight |
| Tabletop Position | Bend MCPs to ~90° while keeping fingers straight |

Exercises are filtered by **injury category** so patients only see what's appropriate for their condition (wrist/forearm, finger/thumb, general, post-surgery).

---

## Requirements

- Python 3.9+ (As of this moment, Mediapipe only supports up to python version 3.12)
- A webcam

Install dependencies:

```bash
pip install mediapipe opencv-python Pillow
```

> The MediaPipe model file (`hand_landmarker.task`) is included in the repository — no separate download needed.

---

## Running the app

```bash
cd /path/to/Landmarker
python app.py
```

To run in Dutch:

```bash
python app.py --lang nl
```

---

## How to use it

### Session flow

```
Injury selection → Exercise menu → Calibration → Countdown (3 s) → Exercise → Report
```

After the report, press Enter to start a new session from injury selection.

### Keyboard controls

| Key | Action |
|---|---|
| ↑ / ↓ or 1–8 | Navigate menus |
| Enter | Confirm selection / advance |
| Space | Confirm pose during calibration / end exercise |
| P | Pause / resume |
| S | Skip calibration (uses default thresholds) |
| Q | Quit |

### Calibration

Before each exercise the app asks you to hold a few reference poses (e.g. open hand, fist, pinch). This takes about 30 seconds and adjusts all detection thresholds to *your* range of motion. Skipping calibration (S) falls back to conservative defaults — calibrating gives better results.

---

## Session reports

After each exercise, two files are saved to the `sessions/` folder:

- **`session_YYYYMMDD_HHMMSS.json`** — full rep-by-rep log with timestamps and accuracy
- **`session_YYYYMMDD_HHMMSS.csv`** — one row per exercise for easy spreadsheet analysis

These are intended for clinicians to track patient compliance and improvement over multiple sessions.

---

## Project structure

```
app.py                  # Entry point
hand_landmarker.task    # MediaPipe model (bundled, do not modify)

tracker/
  hand_tracker.py       # MediaPipe LIVE_STREAM wrapper
  geometry.py           # Landmark math + detection thresholds
  calibration.py        # Per-session calibration against user poses

exercises/
  base.py               # BaseExercise ABC + RepStateMachine
  fist.py / spread.py / pinch.py / ...   # One file per exercise

session/
  session.py            # Session state machine + data model
  reporter.py           # JSON + CSV report writer

ui/
  renderer.py           # All drawing (stateless, PIL + OpenCV)

docs/                   # Architecture notes, clinical design decisions
sessions/               # Auto-created output directory
```

---

## Known limitations

- Tracks one hand at a time
- Claw hand is best observed from the side; the current top-down webcam view is a known limitation
- MediaPipe's Z coordinate (depth) is less reliable than X/Y — useful for rotation correction but can be noisy
- Pause time is included in session duration figures

---

## License

See repository root for license information.
