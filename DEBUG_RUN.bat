@echo off
setlocal enabledelayedexpansion
title GestureX - Build Standalone EXE
color 0B
cd /d "%~dp0"

echo.
echo  ============================================================
echo   GestureX - Packaging Standalone Windows Application
echo  ============================================================
echo.

REM ── Check for Virtual Environment ──────────────────────────────────────────────
if not exist "mac_env\Scripts\python.exe" (
    echo  [ERR] Virtual environment 'mac_env' not found. Run your install script first.
    pause & exit /b 1
)
echo  [OK] Environment verified.

REM ── Install PyInstaller ────────────────────────────────────────────────────────
echo  [1/3] Ensuring PyInstaller is installed...
mac_env\Scripts\python.exe -m pip install pyinstaller --quiet
echo  [OK] Ready.

REM ── Clean previous builds ──────────────────────────────────────────────────────
if exist "dist\GestureX" rmdir /s /q "dist\GestureX"
if exist "build"    rmdir /s /q "build"
if exist "GestureX.spec" del /q "GestureX.spec"

REM ── Execute PyInstaller ────────────────────────────────────────────────────────
echo  [2/3] Compiling EXE (This will take 5-15 minutes. Please wait... )
echo.

mac_env\Scripts\python.exe -m PyInstaller ^
    --name GestureX ^
    --onedir ^
    --console ^
    --noconfirm ^
    --collect-all mediapipe ^
    --collect-all sounddevice ^
    --collect-all speech_recognition ^
    --hidden-import cv2 ^
    --hidden-import pyautogui ^
    --hidden-import numpy ^
    --hidden-import scipy ^
    --hidden-import speech_recognition ^
    --hidden-import sounddevice ^
    main.py

if errorlevel 1 (
    echo.
    echo  [ERR] Build failed. Scroll up to see the Python errors.
    pause & exit /b 1
)

REM ── Copy Required ML Models and Calibration Data ───────────────────────────────
echo.
echo  [3/3] Copying ML models and calibration files into the build...
if exist "face_landmarker.task" copy /y "face_landmarker.task" "dist\GestureX\" >nul
if exist "hand_landmarker.task" copy /y "hand_landmarker.task" "dist\GestureX\" >nul
if exist "cal_data.txt"         copy /y "cal_data.txt"         "dist\GestureX\" >nul
if exist "hand_cal_data.txt"    copy /y "hand_cal_data.txt"    "dist\GestureX\" >nul
echo  [OK] Files copied.

echo.
echo  ============================================================
echo   BUILD COMPLETE!
echo   Your standalone application is located at: 
echo   dist\GestureX\GestureX.exe
echo.
echo   To share this project, just ZIP the entire "dist\GestureX" 
echo   folder and send it. The receiver does NOT need Python!
echo  ============================================================
echo.

set /p OPEN="Open the build folder now? (Y/N): "
if /i "!OPEN!"=="Y" explorer "dist\GestureX"
pause