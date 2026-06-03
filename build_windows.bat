@echo off
REM Build HandTracker for Windows.
REM Run from the Landvenv\ directory on a Windows machine.
REM
REM Prerequisites (run once):
REM   python -m venv venv
REM   venv\Scripts\pip install -r requirements.txt
REM
REM Then run this script:
REM   build_windows.bat

echo =^> Checking environment...
venv\Scripts\python -c "import mediapipe, cv2, PIL; print('deps OK')"
if errorlevel 1 (
    echo ERROR: dependencies not installed. Run: venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

echo =^> Cleaning previous build...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo =^> Running PyInstaller...
venv\Scripts\pyinstaller landvenv.spec

echo.
echo =^> Build complete: dist\HandTracker\
echo     Run with: dist\HandTracker\HandTracker.exe
echo     Or with Dutch UI: dist\HandTracker\HandTracker.exe --lang nl
