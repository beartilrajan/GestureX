<div align="center">

# GestureX

### Hands-Free PC Control

**Control your entire computer with your face, hands, and voice.**  
No mouse. No keyboard. Just a webcam.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-AI-FF6F00?style=for-the-badge&logo=google&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)

</div>

---

## What is GestureX?

GestureX is a software-only accessibility controller that lets you operate your entire PC — move the cursor, click, drag, scroll, and type — without touching a mouse or keyboard.

All you need is a standard webcam and microphone.

---

## Features

- **Face tracking** — move your head to move the cursor, smooth and precise at 165Hz
- **Hand gestures** — touch index+middle fingertips to click, peace sign to right-click, hold to drag
- **Voice input** — speak to type text or trigger 35+ shortcuts, always listening
- **Phone clicker** — open a URL on your phone to use it as a left/right click button while face moves the cursor
- **Three control modes** — Hand only, Face+Hand, or Face only
- **Auto-calibration** — separate calibration for face and hand, saved to disk permanently
- **Mouse fallback** — physical mouse works freely when camera loses tracking
- **Standalone EXE** — share with anyone, no Python needed

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/GestureX.git
cd GestureX
```

### 2. Run the installer

```
Double-click: INSTALL_AND_RUN.bat
```

First time — installs all packages automatically (2–5 min), then launches.  
Every time after — skips setup and launches instantly.

---

## Requirements

| Requirement | Details |
|---|---|
| OS | Windows 10 / 11 |
| Python | 3.11+ (installer handles this) |
| Camera | Built-in or USB webcam |
| Microphone | For voice input |
| Internet | First-time package install + Google STT |

---

## Control Modes

Switch between modes by clicking the buttons in the GestureX panel, or press `M` to cycle.

| Mode | Cursor | Clicks |
|---|---|---|
| **Hand** *(default)* | Palm position | Hand gestures |
| **Face+Hand** | Nose/face | Hand gestures |
| **Face** | Nose/face | Physical mouse or phone |

---

## Hand Gestures

| Gesture | How | Action |
|---|---|---|
| **Touch tips** (quick) | Touch index + middle fingertips briefly | Left click |
| **Touch tips** (hold 0.4s) | Keep fingertips touching | Mouse held — drag anything |
| **Release** | Open fingers | Mouse releases |
| **Peace sign ✌** | Index + middle up, ring + pinky curled | Right click |

> **Drag:** Touch fingertips → hold 0.4s → move your hand/face → open fingers

---

## Face Tracking

Move your head in any direction to move the cursor. GestureX averages 5 nose-area landmarks for stability, filtered through a One-Euro adaptive filter to remove jitter.

When the camera loses your face, your physical mouse takes over instantly.

---

## Phone as Clicker

Use your phone as a dedicated click button while your face moves the cursor — useful for precision clicking without worrying about hand gestures.

1. Launch GestureX
2. Look at the **Phone Clicker** card in the panel — it shows a URL like `http://192.168.x.x:7070`
3. Open that URL on your phone browser (same Wi-Fi)
4. Two big buttons appear — **LEFT CLICK** and **RIGHT CLICK**
5. Your face moves the cursor, phone taps click

> Long-press the LEFT CLICK button on your phone to start a drag.

---

## Voice Input

Voice is **ON by default** — no button needed. Just speak naturally.

### Two modes

| Mode | How to switch | What happens |
|---|---|---|
| **Command mode** (default) | Say *"type mode"* | Speech triggers actions |
| **Typing mode** | Say *"command mode"* | Everything spoken is typed as text |

### Voice commands

| Category | Say this |
|---|---|
| **Scroll** | `scroll up` / `scroll down` / `page up` / `page down` |
| **Browser** | `go back` / `go forward` / `new tab` / `close tab` / `search` / `address bar` |
| **Edit** | `copy` / `paste` / `cut` / `undo` / `redo` / `save` / `select all` |
| **Keys** | `enter` / `escape` / `tab` / `delete` / `backspace` |
| **Mouse** | `click` / `right click` / `double click` |
| **Windows** | `minimise` / `maximise` / `close app` / `show desktop` / `take screenshot` |
| **Mode** | `type mode` / `command mode` |
| **Exit** | `quit` / `exit` |
| *Anything else* | Typed as text into focused app |

---

## Calibration

### Face calibration — press `C`

1. Press `C` in the GestureX window
2. Slowly move your head to all 4 corners of the screen
3. Take 5 seconds — saved automatically to `cal_data.txt`

### Hand calibration — press `H`

1. Switch to **Hand** mode first
2. Press `H`
3. Move your open palm to all 4 corners of the camera frame
4. Take 5 seconds — saved to `hand_cal_data.txt`

> Calibration is saved permanently and loads on every launch. Only redo it if you move your chair or camera.

---

## Keyboard Shortcuts

*(Click the GestureX window first)*

| Key | Action |
|---|---|
| `C` | Face calibrate |
| `H` | Hand calibrate |
| `T` | Toggle microphone |
| `M` | Cycle control mode |
| `D` | Debug overlay |
| `Q` | Quit |

---

## How It Works

```
Webcam (30fps)
    │
    ├── Face Landmarker (MediaPipe AI)
    │     478 landmarks → 5-point nose anchor
    │     → One-Euro filter (removes jitter)
    │     → Dead-zone filter (suppresses tremor)
    │     → Calibrated screen mapping
    │
    ├── Hand Landmarker (MediaPipe AI)
    │     21 joint positions
    │     → Index+Middle tip distance → left click / drag
    │     → Peace sign (MCP comparison) → right click
    │     → Palm centre → cursor (Hand mode)
    │
    └── Voice Thread (sounddevice + Google STT)
          Energy VAD → record speech → resample to 16kHz
          → Google Speech-to-Text → command or type

165Hz mover thread — interpolates cursor between 30fps AI updates
Phone server — HTTP server on port 7070 for phone clicker
```

---

## Project Structure

```
GestureX/
├── main.py                  # Main loop, UI, voice, cursor control, phone server
├── vision_tracker.py        # Face + hand AI tracking, gesture logic, calibration
├── state_manager.py         # Thread-safe shared state
├── voice_handler.py         # Voice system stub
├── face_landmarker.task     # MediaPipe face AI model
├── hand_landmarker.task     # MediaPipe hand AI model
├── requirements.txt         # Python dependencies
├── INSTALL_AND_RUN.bat      # One-click setup and launch
├── BUILD_EXE.bat            # Build standalone EXE
├── RUN_PHONE.bat            # Launch with phone camera
├── cal_data.txt             # Face calibration (auto-generated)
└── hand_cal_data.txt        # Hand calibration (auto-generated)
```

---

## Build Standalone EXE

Share GestureX with anyone — no Python required on their computer.

```
1. Run INSTALL_AND_RUN.bat first
2. Double-click BUILD_EXE.bat
3. Wait 5–15 minutes
4. Output: dist\GestureX\GestureX.exe
5. Zip the dist\GestureX folder and share
```

---

## Phone Camera

Use your Android phone as the webcam instead of your laptop camera.

1. Install **IP Webcam** (free) from the Play Store
2. Open it → tap **Start Server**
3. Note the URL shown (e.g. `http://192.168.1.5:8080`)
4. Edit `RUN_PHONE.bat` and set `PHONE_IP` to your phone's IP
5. Double-click `RUN_PHONE.bat`

Both devices must be on the same Wi-Fi network.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Camera not found | Add `--camera 1` to the python command in `INSTALL_AND_RUN.bat` |
| Face not detecting | Better lighting on your face, sit 40–70 cm from camera |
| Cursor needs too much head movement | Press `C` to recalibrate — move to all corners fully |
| Hand needs too much movement | Press `H` in Hand mode — move palm to all corners |
| Left click not firing | Open fingers completely between clicks to reset the gesture |
| Right click not firing | Raise index + middle clearly, curl ring + pinky down |
| Voice not typing | Click into target app before speaking — GestureX window must not be focused |
| Packages time out | Run: `mac_env\Scripts\python.exe -m pip install mediapipe --timeout 300` |
| Voice energy = 0 | Set your HyperX as default input in Windows Sound Settings |

---

## Tech Stack

| Library | Purpose |
|---|---|
| [MediaPipe](https://developers.google.com/mediapipe) | Face + hand AI landmark detection |
| [OpenCV](https://opencv.org) | Camera capture and display |
| [PyAutoGUI](https://pyautogui.readthedocs.io) | Cursor control and clicks |
| [sounddevice](https://python-sounddevice.readthedocs.io) | Microphone capture (Python 3.14 compatible) |
| [SpeechRecognition](https://github.com/Uberi/speech_recognition) | Google Speech-to-Text |
| [NumPy](https://numpy.org) | Signal processing and math |
| [SciPy](https://scipy.org) | Audio resampling |
| [One-Euro Filter](https://gery.casiez.net/1euro/) | Adaptive pointer smoothing |

---

## License

MIT License — free to use, modify, and distribute.

---

<div align="center">

**GestureX** — Control everything. Touch nothing.

</div>
