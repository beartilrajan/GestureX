@echo off
title MAC – Multimodal Accessibility Controller
cd /d "%~dp0"
echo ==========================================
echo  MAC - Multimodal Accessibility Controller
echo ==========================================
echo.
echo  Controls:
echo    C = Calibrate nose tracking
echo    T = Toggle voice on/off
echo    D = Toggle debug info
echo    Q = Quit
echo.
echo  Voice commands: scroll up/down, search,
echo  copy, paste, save, enter, close app, etc.
echo.
echo  To use phone camera instead:
echo    1. Install "IP Webcam" app on Android
echo    2. Start server in the app
echo    3. Edit RUN_PHONE.bat with your phone IP
echo.
"C:\Users\HP\mac_env\Scripts\python.exe" main.py
echo.
echo Program closed. Press any key to exit.
pause
