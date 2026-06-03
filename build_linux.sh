#!/usr/bin/env bash
# Build HandTracker for Linux using the HandLandmarker312 virtualenv.
# Run from the Landmarker/ directory:
#   bash build_linux.sh

set -e

VENV="/home/codringher/VirtualEnvironments/HandLandmarker312"
PYTHON="$VENV/bin/python"
PYINSTALLER="$VENV/bin/pyinstaller"

echo "==> Checking environment..."
"$PYTHON" -c "import mediapipe, cv2, PIL; print('deps OK')"

echo "==> Cleaning previous build..."
rm -rf build/ dist/

echo "==> Running PyInstaller..."
"$PYINSTALLER" landmarker.spec

echo ""
echo "==> Build complete: dist/HandTracker/"
echo "    Run with: dist/HandTracker/HandTracker"
echo "    Or with Dutch UI: dist/HandTracker/HandTracker --lang nl"
