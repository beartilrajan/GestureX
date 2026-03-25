============================================================
  AirControl - Hands-Free PC Control
  Control your PC with face, hands and voice
============================================================

QUICK START
───────────
  Double-click INSTALL_AND_RUN.bat
  That is it. Everything is automatic.

  First time: installs packages (2-5 min), then launches.
  Every time after: skips setup, launches instantly.


HOW IT WORKS
────────────
  FACE/NOSE  Move your head to move the mouse cursor
  HAND       Gestures trigger clicks and drag
  VOICE      Speak commands or dictate text (always ON)

Gestures:
  Pinch  (thumb+index touch, 3 fingers up) = Hold mouse button
  Peace  (index+middle up, others down)    = Right click

  Short pinch = click
  Hold pinch  = drag (move head while pinching)
  Release     = mouse up

Keys (click AirControl window first):
  C  Calibrate nose tracking
  T  Toggle voice on/off
  D  Toggle debug overlay
  Q  Quit


FIRST RUN - CALIBRATION
────────────────────────
  Press C, then slowly move your head to all 4 corners
  of the screen over 5 seconds. Saved automatically.
  Never need to do again on this computer.


VOICE TYPING
────────────
  Voice is ON by default when AirControl starts.
  Click into any app (Notepad, browser, chat) then speak.
  Words are typed into whichever app is focused.

  If speech is a known command it triggers that action.
  Anything else gets typed as text.


VOICE COMMANDS
──────────────
  scroll up / scroll down       page up / page down
  go back / go forward          search / find
  new tab / close tab           address bar
  copy / paste / cut            undo / redo / save
  select all / delete           enter / escape / tab
  click / right click           double click
  close app / minimise          show desktop
  open settings / open explorer take screenshot
  quit / exit / stop program


BUILD STANDALONE EXE
─────────────────────
  Run INSTALL_AND_RUN.bat first, then BUILD_EXE.bat.
  Output in dist\AirControl\ - zip and share.
  No Python needed on recipient PC.


PHONE CAMERA
────────────
  Install IP Webcam on Android, start server, note IP,
  edit RUN_PHONE.bat with that IP, double-click it.


TROUBLESHOOTING
───────────────
  Camera not found    Add --camera 1 to python command in INSTALL_AND_RUN.bat
  Mouse drifts        Press C to recalibrate
  Voice not typing    Click into target app BEFORE speaking
  Slow/laggy          Press D for FPS, close heavy background apps
============================================================
