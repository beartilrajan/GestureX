# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import os

mediapipe_d, mediapipe_b, mediapipe_h = collect_all('mediapipe')
cv2_d,       cv2_b,       cv2_h       = collect_all('cv2')
try:
    sd_d, sd_b, sd_h = collect_all('sounddevice')
except:
    sd_d, sd_b, sd_h = [], [], []

local_datas = [
    ('state_manager.py',  '.'),
    ('vision_tracker.py', '.'),
    ('voice_handler.py',  '.'),
    ('requirements.txt',  '.'),
]
for f in ['face_landmarker.task','hand_landmarker.task','cal_data.txt']:
    if os.path.exists(f):
        local_datas.append((f, '.'))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=mediapipe_b+cv2_b+sd_b,
    datas=mediapipe_d+cv2_d+sd_d+local_datas,
    hiddenimports=mediapipe_h+cv2_h+sd_h+[
        'speech_recognition','sounddevice','soundfile',
        'pyautogui','numpy','PIL','PIL.Image','cv2',
        'mediapipe','mediapipe.tasks','mediapipe.tasks.python',
        'mediapipe.tasks.python.vision','mediapipe.tasks.python.core',
        'threading','queue','wave','tempfile','ctypes',
        'ctypes.wintypes','math','argparse',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter','matplotlib','scipy','pandas','IPython'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [],
    exclude_binaries=True,
    name='MAC', debug=False,
    strip=False, upx=True, console=True,
)
coll = COLLECT(exe, a.binaries, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='MAC',
)
