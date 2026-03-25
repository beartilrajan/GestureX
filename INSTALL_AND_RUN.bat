@echo off
setlocal enabledelayedexpansion
title GestureX - Setup and Launch
color 0A
cd /d "%~dp0"

echo.
echo  ============================================================
echo   GestureX - Hands-Free PC Control
echo  ============================================================
echo.

REM Check if fully installed
if exist "mac_env\Scripts\python.exe" (
    mac_env\Scripts\python.exe -c "import cv2, mediapipe, pyautogui, speech_recognition, sounddevice" >nul 2>&1
    if not errorlevel 1 (
        echo  [OK] Ready. Launching GestureX...
        goto :LAUNCH
    )
    echo  [..] Some packages missing. Installing now...
    goto :INSTALL
)

REM Check Python
echo  [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [!] Python not found. Opening download page...
    echo      Install Python 3.11, tick "Add Python to PATH", then run again.
    start https://www.python.org/downloads/release/python-3119/
    pause & exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [OK] Python !PYVER!

echo  [2/5] Creating virtual environment...
python -m venv mac_env
if errorlevel 1 ( echo  [ERR] Failed. & pause & exit /b 1 )
echo  [OK] Done.

echo  [3/5] Upgrading pip...
mac_env\Scripts\python.exe -m pip install --upgrade pip --quiet --no-warn-script-location
echo  [OK] Done.

:INSTALL
echo  [4/5] Installing packages (please wait)...
echo.

set OPTS=--timeout 300 --retries 5 --quiet --no-warn-script-location -i https://mirrors.aliyun.com/pypi/simple/

echo  numpy...
:r_numpy
mac_env\Scripts\python.exe -m pip install numpy %OPTS%
if errorlevel 1 ( echo  Retrying... & goto r_numpy )
echo  [OK] numpy

echo  pillow...
:r_pillow
mac_env\Scripts\python.exe -m pip install pillow %OPTS%
if errorlevel 1 ( echo  Retrying... & goto r_pillow )
echo  [OK] pillow

echo  scipy...
:r_scipy
mac_env\Scripts\python.exe -m pip install scipy %OPTS%
if errorlevel 1 ( echo  Retrying... & goto r_scipy )
echo  [OK] scipy

echo  opencv-python...
:r_cv2
mac_env\Scripts\python.exe -m pip install opencv-python %OPTS%
if errorlevel 1 ( echo  Retrying... & goto r_cv2 )
echo  [OK] opencv-python

echo  pyautogui...
:r_pag
mac_env\Scripts\python.exe -m pip install pyautogui %OPTS%
if errorlevel 1 ( echo  Retrying... & goto r_pag )
echo  [OK] pyautogui

echo  SpeechRecognition...
:r_sr
mac_env\Scripts\python.exe -m pip install SpeechRecognition %OPTS%
if errorlevel 1 ( echo  Retrying... & goto r_sr )
echo  [OK] SpeechRecognition

echo  sounddevice (microphone)...
:r_sd
mac_env\Scripts\python.exe -m pip install sounddevice %OPTS%
if errorlevel 1 ( echo  Retrying... & goto r_sd )
echo  [OK] sounddevice

echo  mediapipe (largest package)...
:r_mp
mac_env\Scripts\python.exe -m pip install mediapipe %OPTS%
if errorlevel 1 ( echo  Retrying... & goto r_mp )
echo  [OK] mediapipe

echo.
echo  [5/5] Verifying...
mac_env\Scripts\python.exe -c "import cv2, mediapipe, pyautogui, speech_recognition, sounddevice, numpy, scipy; print('[OK] All packages verified.')"
if errorlevel 1 (
    echo  [ERR] Verification failed. Run this file again.
    pause & exit /b 1
)

echo.
echo  ============================================================
echo   Setup complete! Launching GestureX...
echo  ============================================================
echo.
timeout /t 2 /nobreak >nul

:LAUNCH
echo  Controls: C=Calibrate  T=Voice  D=Debug  Q=Quit
echo  Voice is ON by default - just speak!
echo.
mac_env\Scripts\python.exe main.py %*
echo.
echo  ============================================================
echo   GestureX closed. Press any key to exit.
echo  ============================================================
pause
