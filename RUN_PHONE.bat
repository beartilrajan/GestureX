@echo off
title AirControl - Phone Camera Mode
cd /d "%~dp0"

REM *** CHANGE THIS IP TO YOUR PHONE'S IP ***
set PHONE_IP=192.168.1.5
set PHONE_PORT=8080

echo.
echo  AirControl - Phone Camera Mode
echo  URL: http://%PHONE_IP%:%PHONE_PORT%/video
echo.
echo  Setup: Install "IP Webcam" on Android, tap Start Server,
echo  note the IP shown, update PHONE_IP above to match.
echo.

if not exist "mac_env\Scripts\python.exe" (
    echo  [ERR] Run INSTALL_AND_RUN.bat first.
    pause & exit /b 1
)

mac_env\Scripts\python.exe main.py --phone "http://%PHONE_IP%:%PHONE_PORT%/video"
echo.
echo  AirControl closed. Press any key to exit.
pause
