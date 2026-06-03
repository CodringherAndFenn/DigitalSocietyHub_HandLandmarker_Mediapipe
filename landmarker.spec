# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Hand Rehab Tracker (HandTracker).
Builds a one-folder distribution for both Linux and Windows.

Linux build:
    pyinstaller landmarker.spec

Windows build (run on Windows):
    pyinstaller landmarker.spec
"""
from PyInstaller.utils.hooks import collect_all, collect_data_files

mp_datas, mp_binaries, mp_hidden = collect_all('mediapipe')
cv2_datas, cv2_binaries, cv2_hidden = collect_all('cv2')

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=mp_binaries + cv2_binaries,
    datas=[
        ('hand_landmarker.task', '.'),
        ('fonts',                'fonts'),
        ('translations',         'translations'),
        ('exercises',            'exercises'),
        ('session',              'session'),
        ('tracker',              'tracker'),
        ('ui',                   'ui'),
    ] + mp_datas + cv2_datas,
    hiddenimports=mp_hidden + cv2_hidden + [
        'mediapipe',
        'mediapipe.tasks',
        'mediapipe.tasks.python',
        'mediapipe.tasks.python.vision',
        'mediapipe.tasks.python.core',
        'mediapipe.tasks.python.components',
        'PIL',
        'PIL._imaging',
        'numpy',
        'translations',
        'translations.en',
        'translations.nl',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'scipy', 'IPython'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HandTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='HandTracker',
)
