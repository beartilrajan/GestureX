@echo off
setlocal enabledelayedexpansion
title AirControl - Build EXE
color 0B
cd /d "%~dp0"

echo.
echo  ============================================================
echo   AirControl - Build Standalone EXE
echo  ============================================================
echo.

REM ── Check packages installed ──────────────────────────────────────────────────
if not exist "mac_env\Scripts\python.exe" (
    echo  [ERR] Run INSTALL_AND_RUN.bat first.
    pause & exit /b 1
)
mac_env\Scripts\python.exe -c "import cv2, mediapipe" >nul 2>&1
if errorlevel 1 (
    echo  [ERR] Packages not installed. Run INSTALL_AND_RUN.bat first.
    pause & exit /b 1
)
echo  [OK] Packages verified.

REM ── Install PyInstaller ───────────────────────────────────────────────────────
echo  [1/4] Installing PyInstaller...
mac_env\Scripts\python.exe -m pip install pyinstaller --quiet --no-warn-script-location -i https://mirrors.aliyun.com/pypi/simple/
echo  [OK] Done.

REM ── Get cv2 path ──────────────────────────────────────────────────────────────
echo  [2/4] Finding package locations...
for /f "delims=" %%i in ('mac_env\Scripts\python.exe -c "import cv2,os; print(os.path.dirname(cv2.__file__))"') do set CV2_PATH=%%i
for /f "delims=" %%i in ('mac_env\Scripts\python.exe -c "import mediapipe,os; print(os.path.dirname(mediapipe.__file__))"') do set MP_PATH=%%i
echo  cv2 path: !CV2_PATH!
echo  mediapipe path: !MP_PATH!

REM ── Clean old build ───────────────────────────────────────────────────────────
if exist "dist\AirControl" rmdir /s /q "dist\AirControl"
if exist "build"    rmdir /s /q "build"

REM ── Build ─────────────────────────────────────────────────────────────────────
echo  [3/4] Building EXE (5-15 min)...
echo.

mac_env\Scripts\python.exe -m PyInstaller ^
    --name AirControl ^
    --onedir ^
    --console ^
    --noconfirm ^
    --paths "mac_env\Lib\site-packages" ^
    --collect-all cv2 ^
    --collect-all mediapipe ^
    --collect-all sounddevice ^
    --collect-all speech_recognition ^
    --hidden-import cv2 ^
    --hidden-import mediapipe ^
    --hidden-import mediapipe.tasks ^
    --hidden-import mediapipe.tasks.python ^
    --hidden-import mediapipe.tasks.python.vision ^
    --hidden-import pyautogui ^
    --hidden-import numpy ^
    --hidden-import sounddevice ^
    --hidden-import speech_recognition ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import threading ^
    --hidden-import queue ^
    --hidden-import wave ^
    --hidden-import ctypes ^
    --hidden-import math ^
    --add-data "state_manager.py;." ^
    --add-data "vision_tracker.py;." ^
    --add-data "voice_handler.py;." ^
    main.py

if errorlevel 1 (
    echo.
    echo  [ERR] Build failed. See errors above.
    pause & exit /b 1
)

REM ── Copy data files ───────────────────────────────────────────────────────────
echo  [4/4] Copying model and data files...
if exist "face_landmarker.task" copy /y "face_landmarker.task" "dist\AirControl\" >nul
if exist "hand_landmarker.task" copy /y "hand_landmarker.task" "dist\AirControl\" >nul
if exist "cal_data.txt"         copy /y "cal_data.txt"         "dist\AirControl\" >nul
if exist "README.txt"           copy /y "README.txt"           "dist\AirControl\" >nul
echo  [OK] Done.

echo.
echo  ============================================================
echo   BUILD COMPLETE!
echo   EXE is at: dist\AirControl\MAC.exe
echo   Zip the dist\AirControl folder to share - no Python needed.
echo  ============================================================
echo.
set /p OPEN="Open dist\AirControl folder? (Y/N): "
if /i "!OPEN!"=="Y" explorer "dist\AirControl"
pause
