"""
main.py - GestureX | Hands-Free PC Control
High-res UI: 1280x720, cinematic dark glass aesthetic
"""
import sys, time, logging, threading, queue, os
import ctypes, ctypes.wintypes, platform, argparse, math
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
import cv2, pyautogui, numpy as np
from state_manager import app_state
from vision_tracker import EyeTracker, HandTracker

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("GestureX")
pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0.0

class CameraStream:
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) 
        self.ret, self.frame = self.cap.read()
        self.running = True
        threading.Thread(target=self.update, daemon=True, name="CameraWorker").start()

    def update(self):
        while self.running and app_state.running:
            ret, frame = self.cap.read()
            if ret:
                self.ret = ret; self.frame = frame
            time.sleep(0.01)

    def read(self):
        return self.ret, self.frame.copy() if self.ret else None

    def release(self):
        self.running = False; self.cap.release()

CONTROL_MODES  = ["HAND", "FULL", "PHONE"]
control_mode   = "HAND"   

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
        return ip
    except: return "127.0.0.1"

LOCAL_IP = get_local_ip()

class PhoneUIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200); self.send_header('Content-type', 'text/html'); self.end_headers()
            # NEW: 2x2 Grid with Continuous Scroll Logic
            html = """
            <!DOCTYPE html><html><head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
            <style>
                body { margin: 0; padding: 0; background: #0a0a0a; display: flex; flex-direction: column; height: 100vh; font-family: sans-serif; user-select: none; -webkit-user-select: none; touch-action: none; }
                .row { display: flex; flex: 1; }
                .btn { flex: 1; margin: 10px; border-radius: 20px; border: none; font-size: 24px; font-weight: bold; color: white; display: flex; align-items: center; justify-content: center; text-align: center; }
                #left { background: #00d250; } #right { background: #00aaff; }
                #up { background: #ffaa00; } #down { background: #ff4444; }
                .btn:active { opacity: 0.6; transform: scale(0.98); }
            </style></head><body>
                <div class="row">
                    <div class="btn" id="left" onpointerdown="send('left_down')" onpointerup="send('left_up')">LEFT CLICK<br><span style="font-size:14px; font-weight:normal; margin-top:5px;">(Hold to Drag)</span></div>
                    <div class="btn" id="right" onpointerdown="send('right')">RIGHT CLICK</div>
                </div>
                <div class="row">
                    <div class="btn" id="up" onpointerdown="startScroll('up')" onpointerup="stopScroll()" onpointerleave="stopScroll()">SCROLL UP</div>
                    <div class="btn" id="down" onpointerdown="startScroll('down')" onpointerup="stopScroll()" onpointerleave="stopScroll()">SCROLL DOWN</div>
                </div>
                <script>
                    function send(action) { fetch('/' + action, {method: 'POST'}); }
                    let scroller;
                    function startScroll(dir) { scroller = setInterval(() => send('scroll_' + dir), 50); }
                    function stopScroll() { clearInterval(scroller); }
                    document.addEventListener('contextmenu', event => event.preventDefault());
                </script>
            </body></html>
            """
            self.wfile.write(html.encode())
        else: self.send_response(404); self.end_headers()

    def do_POST(self):
        if self.path == '/left_down': app_state.set("phone_action", "left_down")
        elif self.path == '/left_up': app_state.set("phone_action", "left_up")
        elif self.path == '/right':   app_state.set("phone_action", "right")
        elif self.path == '/scroll_up': app_state.set("phone_action", "scroll_up")
        elif self.path == '/scroll_down': app_state.set("phone_action", "scroll_down")
        self.send_response(200); self.end_headers()

    def log_message(self, format, *args): pass

def run_phone_server():
    server = HTTPServer(('0.0.0.0', 5000), PhoneUIHandler)
    logger.info("Phone Controller running at http://%s:5000", LOCAL_IP)
    server.serve_forever()

app_state.set("phone_action", None)
threading.Thread(target=run_phone_server, daemon=True).start()

VOICE_COMMANDS = {
    "open browser":    lambda: os.system("start brave"),
    "search google":   lambda: os.system("start brave \"https://www.google.com\""),
    "scroll up":       lambda: pyautogui.scroll(5),
    "scroll down":     lambda: pyautogui.scroll(-5),
    "go back":         lambda: pyautogui.hotkey("alt","left"),
    "search":          lambda: pyautogui.hotkey("ctrl","f"),
    "new tab":         lambda: pyautogui.hotkey("ctrl","t"),
    "close tab":       lambda: pyautogui.hotkey("ctrl","w"),
    "copy":            lambda: pyautogui.hotkey("ctrl","c"),
    "paste":           lambda: pyautogui.hotkey("ctrl","v"),
    "undo":            lambda: pyautogui.hotkey("ctrl","z"),
    "enter":           lambda: pyautogui.press("enter"),
    "escape":          lambda: pyautogui.press("escape"),
    "close window":    lambda: pyautogui.hotkey("alt","f4"),
    "show desktop":    lambda: pyautogui.hotkey("win","d"),
    "quit":            lambda: app_state.set("running", False),
}

def _execute_command(phrase):
    pl = phrase.lower().strip()
    for cmd in sorted(VOICE_COMMANDS, key=len, reverse=True):
        if cmd in pl:
            try: VOICE_COMMANDS[cmd]()
            except Exception as e: logger.warning("CMD err: %s", e)
            return True
    return False

voice_queue   = queue.Queue()
voice_enabled = threading.Event()   
voice_enabled.set()                 
voice_on      = True                
voice_mode    = "command"           
voice_ready   = False

def _voice_worker():
    global voice_ready
    try:
        import sounddevice as sd
        import speech_recognition as sr
        devices = sd.query_devices(); input_device_id = sd.default.device[0]
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0 and 'hyper' in dev['name'].lower():
                input_device_id = i; break
        dev_info = sd.query_devices(input_device_id)
        RATE = int(dev_info['default_samplerate'])
        voice_ready = True
    except Exception as e: return

    import queue as _queue
    
    CHUNK = int(RATE * 0.05); SILENCE_END = 12; MIN_SPEECH = 2; MAX_SPEECH = 150; SILENCE_DB = 150
    rec = sr.Recognizer(); audio_q = _queue.Queue()

    def _callback(indata, frames, time_info, status): audio_q.put(indata.copy())
    stream = sd.InputStream(samplerate=RATE, channels=1, dtype='int16', device=input_device_id, callback=_callback, blocksize=CHUNK)
    stream.start()

    def _async_process(data, s_rate):
        if s_rate != 16000:
            from scipy.signal import resample
            data = resample(data, int(len(data) * 16000 / s_rate)).astype(np.int16)
        aud = sr.AudioData(data.tobytes(), 16000, 2)
        try:
            text = rec.recognize_google(aud).strip()
            if text: voice_queue.put(text)
        except: pass

    while app_state.running:
        if not voice_enabled.is_set():
            time.sleep(0.1)
            while not audio_q.empty(): audio_q.get()
            continue
        try:
            frames = []; speech_detected = False
            while app_state.running and voice_enabled.is_set():
                try: chunk = audio_q.get(timeout=0.5)
                except _queue.Empty: continue
                energy = int(np.abs(chunk).mean())
                if energy > SILENCE_DB: speech_detected = True; frames.append(chunk); break

            if not speech_detected: continue

            silent = 0
            while app_state.running and voice_enabled.is_set():
                try: chunk = audio_q.get(timeout=0.5)
                except _queue.Empty:
                    silent += 1
                    if silent >= SILENCE_END: break
                    continue
                energy = int(np.abs(chunk).mean())
                frames.append(chunk)
                if energy < SILENCE_DB: silent += 1
                else: silent = 0
                if silent >= SILENCE_END or len(frames) >= MAX_SPEECH: break

            if len(frames) < MIN_SPEECH: continue
            audio_data = np.concatenate(frames, axis=0)
            
            threading.Thread(target=_async_process, args=(audio_data, RATE), daemon=True).start()
            
        except: time.sleep(0.1)

    stream.stop(); stream.close()

def _type_text(text):
    if not text: return
    try: pyautogui.write(text + " ", interval=0.0)
    except: pass

class CursorMapper:
    def __init__(self): self.sw, self.sh = pyautogui.size()
    def to_screen(self, nx, ny): 
        return int(nx * (self.sw - 1)), int(ny * (self.sh - 1))

class SmoothMover:
    def __init__(self, hz=165):
        self.sw, self.sh = pyautogui.size()
        self._tx, self._ty = pyautogui.position()
        self._cx = float(self._tx); self._cy = float(self._ty)
        self._lock = threading.Lock(); self._interval = 1.0/hz; self._lerp = 0.22
        self._active = True; self._running = True
        threading.Thread(target=self._loop, daemon=True, name="Mover").start()

    def set_target(self, px, py, active=True):
        with self._lock: self._tx = float(px); self._ty = float(py); self._active = active

    def _loop(self):
        while self._running and app_state.running:
            t0 = time.perf_counter()
            with self._lock: tx,ty,active = self._tx,self._ty,self._active
            if active:
                self._cx += (tx-self._cx)*self._lerp; self._cy += (ty-self._cy)*self._lerp
                out_x = max(0, min(self.sw - 1, int(round(self._cx))))
                out_y = max(0, min(self.sh - 1, int(round(self._cy))))
                try: pyautogui.moveTo(out_x, out_y, _pause=False)
                except: pass
            else:
                real = pyautogui.position()
                self._cx,self._cy = float(real[0]),float(real[1])
                with self._lock: self._tx,self._ty = self._cx,self._cy
            rem = self._interval-(time.perf_counter()-t0)
            if rem>0: time.sleep(rem)

    def stop(self): self._running=False

# ══════════════════════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════════════════════
UI_W, UI_H   = 1280, 720
CAM_W, CAM_H = 854, 480    
PANEL_X      = CAM_W       
PANEL_W      = UI_W - CAM_W  

TOGGLE_BTN = { "HAND": {}, "FULL": {}, "PHONE": {} }

BG = (8,10,14); PANEL_BG = (14,17,24); GLASS = (22,28,40); GLASS_LITE = (30,38,55); MID = (18,24,38)
BORDER = (45,58,85); BORDER_LIT = (70,95,140); CYAN = (30,220,180); AMBER = (0,170,255)
GREEN_NEON = (0,210,80); CRIMSON = (40,40,220); PURPLE = (200,80,200); GOLD = (30,190,220)
WHITE = (240,245,250); GRAY = (130,145,165); DIM = (70,85,105)

def _blend(img, x, y, w, h, color, alpha):
    roi = img[y:y+h, x:x+w]; overlay = np.full_like(roi, color)
    cv2.addWeighted(overlay, alpha, roi, 1-alpha, 0, roi)
    img[y:y+h, x:x+w] = roi

def _rrect(img, x, y, w, h, r, color, filled=True, thick=1):
    if filled:
        cv2.rectangle(img, (x+r,y), (x+w-r,y+h), color, -1); cv2.rectangle(img, (x, y+r), (x+w, y+h-r), color, -1)
        for cx,cy in [(x+r,y+r),(x+w-r,y+r),(x+r,y+h-r),(x+w-r,y+h-r)]: cv2.circle(img, (cx,cy), r, color, -1, cv2.LINE_AA)
    else:
        cv2.line(img,(x+r,y),(x+w-r,y),color,thick,cv2.LINE_AA); cv2.line(img,(x+r,y+h),(x+w-r,y+h),color,thick,cv2.LINE_AA)
        cv2.line(img,(x,y+r),(x,y+h-r),color,thick,cv2.LINE_AA); cv2.line(img,(x+w,y+r),(x+w,y+h-r),color,thick,cv2.LINE_AA)
        cv2.ellipse(img,(x+r,y+r),(r,r),180,0,90, color,thick,cv2.LINE_AA); cv2.ellipse(img,(x+w-r,y+r),(r,r),270,0,90, color,thick,cv2.LINE_AA)
        cv2.ellipse(img,(x+r,y+h-r),(r,r), 90,0,90, color,thick,cv2.LINE_AA); cv2.ellipse(img,(x+w-r,y+h-r),(r,r),0,0,90, color,thick,cv2.LINE_AA)

def _txt(img, text, x, y, scale, color, bold=False, aa=True):
    cv2.putText(img, text, (x,y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2 if bold else 1, cv2.LINE_AA if aa else cv2.LINE_8)

def _glow_circle(img, cx, cy, r, color, pulse=False, t=0.0):
    if pulse:
        cv2.circle(img, (cx,cy), int(r * (1.4 + 0.4*abs(math.sin(t*2.5)))), tuple(int(c*0.2) for c in color), -1, cv2.LINE_AA)
        cv2.circle(img, (cx,cy), int(r * (1.1 + 0.2*abs(math.sin(t*2.5+1)))), tuple(int(c*0.4) for c in color), -1, cv2.LINE_AA)
    cv2.circle(img, (cx,cy), r+3, tuple(int(c*0.3) for c in color), -1, cv2.LINE_AA)
    cv2.circle(img, (cx,cy), r, color, -1, cv2.LINE_AA)
    cv2.circle(img, (cx-r//4,cy-r//4), max(1,r//3), tuple(min(255,int(c*1.5)) for c in color), -1, cv2.LINE_AA)

def _hbar(img, x, y, w, h, pct, color):
    _rrect(img, x, y, w, h, h//2, (25,32,48))
    if pct > 0:
        fw = max(h, int(w * pct/100))
        _rrect(img, x, y, fw, h, h//2, color)
        _rrect(img, x, y, fw, h, h//2, tuple(int(c*0.4) for c in color), filled=False, thick=2)

def _separator(img, x, y, w, color=BORDER): cv2.line(img, (x,y), (x+w,y), color, 1, cv2.LINE_AA)
def _section_header(img, label, x, y, w, color):
    cv2.rectangle(img, (x,y), (x+2,y+12), color, -1); _txt(img, label, x+8, y+10, 0.38, GRAY)

def _draw_ui(cam_frame, face_res, hand_gesture, voice_on, voice_mode, control_mode,
             last_heard, eye_cal_text, eye_cal_pct, hand_cal_text, hand_cal_pct, fps, t):

    canvas = np.zeros((UI_H, UI_W, 3), dtype=np.uint8); canvas[:] = BG
    for gx in range(0, UI_W, 40): cv2.line(canvas, (gx,0), (gx,UI_H), (16,20,28), 1)
    for gy in range(0, UI_H, 40): cv2.line(canvas, (0,gy), (UI_W,gy), (16,20,28), 1)

    cam_h, cam_w = cam_frame.shape[:2]
    scale = min(CAM_W/cam_w, CAM_H/cam_h)
    nw, nh = int(cam_w*scale), int(cam_h*scale)
    resized = cv2.resize(cam_frame, (nw,nh), interpolation=cv2.INTER_LANCZOS4)
    ox = (CAM_W-nw)//2; oy = (CAM_H-nh)//2 + 48
    canvas[oy:oy+nh, ox:ox+nw] = resized

    for i in range(6): _rrect(canvas, ox-i, oy-i, nw+i*2, nh+i*2, 4, tuple(int(c*(0.12 - i*0.018)) for c in CYAN), filled=False, thick=1)

    cal_pct = max(eye_cal_pct, hand_cal_pct) * 100
    cal_text = eye_cal_text if eye_cal_pct > 0 else (hand_cal_text if hand_cal_pct > 0 else "")
    if cal_pct > 0:
        bar_w = 400; bx = ox + (nw // 2) - (bar_w // 2); by = oy + nh - 40
        _blend(canvas, bx-10, by-30, bar_w+20, 60, (0,0,0), 0.7)
        _hbar(canvas, bx, by, bar_w, 14, cal_pct, CYAN)
        _txt(canvas, cal_text, bx, by-10, 0.45, CYAN, bold=True)

    nose_ok = face_res is not None and face_res.cursor_x is not None
    fc = GREEN_NEON if nose_ok else CRIMSON
    _blend(canvas, ox+8, oy+8, 170, 26, (0,0,0), 0.6)
    _rrect(canvas, ox+8, oy+8, 170, 26, 4, fc, filled=False, thick=1)
    _glow_circle(canvas, ox+22, oy+22, 5, fc, pulse=nose_ok, t=t)
    _txt(canvas, "FACE LOCKED" if nose_ok else "NO FACE", ox+32, oy+26, 0.42, fc, bold=True)

    _blend(canvas, 0, 0, CAM_W, 46, (0,0,0), 0.7); cv2.rectangle(canvas, (0,0), (CAM_W,46), GLASS, -1); _separator(canvas, 0, 46, CAM_W, BORDER)
    cv2.rectangle(canvas, (14,10), (30,36), CYAN, -1); cv2.rectangle(canvas, (34,10), (50,36), CYAN, -1); cv2.rectangle(canvas, (14,10), (50,20), CYAN, -1)
    _txt(canvas, "GestureX", 58, 33, 0.68, WHITE, bold=True); _txt(canvas, "Hands-Free PC Control", 168, 33, 0.38, GRAY)

    sy = oy+nh+4
    if UI_H - sy > 20:
        _blend(canvas, 0, sy, CAM_W, UI_H-sy, (0,0,0), 0.4); cv2.rectangle(canvas, (0,sy), (CAM_W, UI_H), GLASS, -1)
        gc = CYAN if hand_gesture in ("L-Hold", "L-Pinch", "SCROLL") else (AMBER if hand_gesture == "R-CLICK" else GREEN_NEON)
        _glow_circle(canvas, 20, sy+16, 6, gc, t=t); _txt(canvas, f"Hand: {hand_gesture}", 34, sy+20, 0.45, gc, bold=True)
        if last_heard: _txt(canvas, f'"{last_heard[:55]}"', 14, sy+42, 0.4, WHITE)

    px, pw = PANEL_X, PANEL_W
    cv2.rectangle(canvas, (px,0), (UI_W,UI_H), PANEL_BG, -1)
    pp = px + 16; pw2 = pw - 32; cy2 = 10

    _txt(canvas, "GESTURE", pp, cy2+16, 0.62, WHITE, bold=True); _txt(canvas, "X", pp+100, cy2+16, 0.62, CYAN, bold=True)
    _separator(canvas, pp, cy2+24, pw2, BORDER_LIT); cy2 += 32

    mode_defs = [("HAND", "Hand Only", AMBER), ("FULL", "Face+Hand", CYAN), ("PHONE", "Face+Phone", PURPLE)]
    btn_h = 34; gap = 6; btn_w = (pw2 - gap*2) // 3
    _txt(canvas, "[M] CONTROL MODE", pp, cy2+10, 0.36, BORDER_LIT); cy2 += 14

    for i, (m_key, m_lbl, m_col) in enumerate(mode_defs):
        bx = pp + i*(btn_w + gap); active = (control_mode == m_key)
        if active:
            _rrect(canvas, bx, cy2, btn_w, btn_h, 5, m_col, filled=True)
            _txt(canvas, m_lbl, bx + btn_w//2 - len(m_lbl)*4, cy2+22, 0.38, BG, bold=True)
        else:
            _rrect(canvas, bx, cy2, btn_w, btn_h, 5, MID); _rrect(canvas, bx, cy2, btn_w, btn_h, 5, m_col, filled=False, thick=1)
            _txt(canvas, m_lbl, bx + btn_w//2 - len(m_lbl)*4, cy2+22, 0.36, m_col)
        TOGGLE_BTN[m_key] = {"x": bx, "y": cy2, "w": btn_w, "h": btn_h}
    cy2 += btn_h + 10

    card_h = 105
    cv2.rectangle(canvas, (pp,cy2), (pp+pw2,cy2+card_h), GLASS, -1)
    if control_mode == "PHONE":
        _rrect(canvas, pp, cy2, pw2, card_h, 5, PURPLE, filled=False, thick=1)
        _section_header(canvas, "PHONE CONTROLLER", pp+8, cy2+8, pw2, PURPLE)
        _glow_circle(canvas, pp+16, cy2+34, 7, PURPLE, pulse=True, t=t)
        _txt(canvas, "SERVER RUNNING", pp+30, cy2+38, 0.46, PURPLE, bold=True)
        _separator(canvas, pp+8, cy2+50, pw2-16, BORDER)
        _txt(canvas, f"Open browser on phone:", pp+10, cy2+64, 0.38, GRAY)
        _txt(canvas, f"http://{LOCAL_IP}:5000", pp+10, cy2+82, 0.46, WHITE, bold=True)
    else:
        bc = gc if 'gc' in dir() else DIM
        _rrect(canvas, pp, cy2, pw2, card_h, 5, bc, filled=False, thick=1)
        _section_header(canvas, "HAND GESTURES", pp+8, cy2+8, pw2, BORDER_LIT)
        _glow_circle(canvas, pp+16, cy2+34, 7, gc, t=t)
        _txt(canvas, f"State: {hand_gesture}", pp+30, cy2+38, 0.46, gc, bold=True)
        _separator(canvas, pp+8, cy2+50, pw2-16, BORDER)
        _txt(canvas, "Two Fingers Up = Scroll Page", pp+10, cy2+64, 0.33, WHITE)
        _txt(canvas, "Thumb+Index = L-Click / Drag", pp+10, cy2+80, 0.33, WHITE)
        _txt(canvas, "Thumb+Pinky = R-Click", pp+10, cy2+96, 0.33, WHITE)
    cy2 += card_h + 6

    card_h = 70
    cv2.rectangle(canvas, (pp,cy2), (pp+pw2,cy2+card_h), GLASS, -1)
    vbc = PURPLE if voice_mode=="type" else (AMBER if voice_on else BORDER)
    _rrect(canvas, pp, cy2, pw2, card_h, 5, vbc, filled=False, thick=1)
    _section_header(canvas, "VOICE", pp+8, cy2+8, pw2, vbc)
    _glow_circle(canvas, pp+16, cy2+34, 7, AMBER if voice_on else DIM, pulse=voice_on, t=t)
    _txt(canvas, "COMMAND MODE" if voice_mode == "command" else "TYPING MODE", pp+30, cy2+38, 0.46, AMBER, bold=True)
    if last_heard: _txt(canvas, f'"{last_heard[:24]}"', pp+10, cy2+60, 0.34, WHITE)
    cy2 += card_h + 6

    # FIX: Corrected the 4-grid layout to include the Mic Toggle and Mode Switch
    for kx, ky, k, desc in [(pp+8, cy2+26, "[", "Face Cal"), (pp+pw2//2, cy2+26, "]", "Hand Cal"), (pp+8, cy2+48, "\\", "Mic On/Off"), (pp+pw2//2, cy2+48, "=", "Switch Mode")]:
        _rrect(canvas, kx, ky-12, 17, 16, 3, GLASS_LITE); _txt(canvas, k, kx+4, ky, 0.36, GOLD, bold=True); _txt(canvas, desc, kx+22, ky, 0.36, WHITE)

    return canvas

def run():
    global voice_on, voice_mode, control_mode
    app_state.set("debug", False)

    cam_stream = CameraStream(0)
    time.sleep(1) 

    mapper = CursorMapper(); mover = SmoothMover(hz=165)
    eye_t = EyeTracker(); hand_t = HandTracker()

    threading.Thread(target=_voice_worker, daemon=True, name="Voice").start()

    win = "GestureX"; cv2.namedWindow(win, cv2.WINDOW_NORMAL); cv2.resizeWindow(win, UI_W, UI_H)

    mode_ref = [control_mode]
    def _on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            for mk, r in TOGGLE_BTN.items():
                if r["x"] <= x <= r["x"]+r["w"] and r["y"] <= y <= r["y"]+r["h"]: param[0] = mk
    cv2.setMouseCallback(win, _on_mouse, mode_ref)

    last_px, last_py = mapper.sw//2, mapper.sh//2
    voice_on = True; voice_mode = "command"; last_heard = ""
    t_prev = time.perf_counter(); fps = 30.0; t_anim = 0.0

    while app_state.running:
        ret, frame = cam_stream.read()
        if not ret or frame is None: 
            time.sleep(0.01)
            continue

        control_mode = mode_ref[0]
        t_now = time.perf_counter(); fps = 0.9*fps + 0.1*(1.0/max(t_now-t_prev, 1e-6)); t_prev = t_now; t_anim += 0.033
        frame = cv2.flip(frame, 1)

        if control_mode in ("FULL", "PHONE"):
            face_res = eye_t.process(frame)
            if face_res.cursor_x is not None:
                last_px, last_py = mapper.to_screen(face_res.cursor_x, face_res.cursor_y)
                mover.set_target(last_px, last_py, active=True)
            else: mover.set_target(last_px, last_py, active=False)
        else: face_res = None

        if control_mode in ("FULL", "HAND"):
            hand_cursor = (control_mode == "HAND")
            hand_res = hand_t.process(frame, hand_cursor=hand_cursor)
            if hand_cursor and hand_res.cursor_x is not None:
                last_px, last_py = mapper.to_screen(hand_res.cursor_x, hand_res.cursor_y)
                mover.set_target(last_px, last_py, active=True)
            elif hand_cursor and hand_res.cursor_x is None:
                mover.set_target(last_px, last_py, active=False)

            try:
                # NEW: Dispatch Hand Scroll Events
                if hand_res.scroll_dy != 0: pyautogui.scroll(hand_res.scroll_dy)
                
                if hand_res.mouse_down: pyautogui.mouseDown(last_px, last_py, _pause=False)
                if hand_res.mouse_up: pyautogui.mouseUp(last_px, last_py, _pause=False)
                if hand_res.left_click: pyautogui.click(last_px, last_py, _pause=False)
                if hand_res.right_click: pyautogui.rightClick(last_px, last_py, _pause=False)
            except: pass

        if control_mode == "PHONE":
            hand_res = None
            action = app_state.get("phone_action")
            if action:
                try:
                    if action == "left_down": pyautogui.mouseDown(last_px, last_py, _pause=False)
                    elif action == "left_up": pyautogui.mouseUp(last_px, last_py, _pause=False)
                    elif action == "right":   pyautogui.rightClick(last_px, last_py, _pause=False)
                    # NEW: Dispatch Phone Scroll Events
                    elif action == "scroll_up": pyautogui.scroll(150)
                    elif action == "scroll_down": pyautogui.scroll(-150)
                except: pass
                app_state.set("phone_action", None) 

        try:
            text = voice_queue.get_nowait()
            if text:
                last_heard = text; tl = text.lower().strip()
                
                if tl in ("type mode", "typing mode", "start typing"): 
                    voice_mode = "type"
                elif tl in ("command mode", "exit typing", "stop typing"): 
                    voice_mode = "command"
                elif voice_mode == "command":
                    if not _execute_command(text): _type_text(text)
                else: 
                    _type_text(text)
        except queue.Empty: pass

        canvas = _draw_ui(
            frame, face_res, hand_t.gesture if hand_res else "none",
            voice_on, voice_mode, control_mode, last_heard,
            eye_t.cal_instruction, eye_t.cal_progress, 
            hand_t.cal_instruction, hand_t.cal_progress,
            fps, t_anim
        )

        cv2.imshow(win, canvas)

        key = cv2.waitKey(1) & 0xFF
        if key == 27: 
            app_state.set("running", False)
        elif key == ord("["): 
            eye_t.start_calibration()
        elif key == ord("]"): 
            hand_t.start_calibration()
        elif key == ord("\\"): 
            voice_on = not voice_on
            if voice_on: voice_enabled.set()
            else: voice_enabled.clear()
        elif key == ord("="):
            idx = CONTROL_MODES.index(control_mode)
            mode_ref[0] = CONTROL_MODES[(idx+1) % len(CONTROL_MODES)]

    app_state.set("running", False); voice_enabled.clear()
    mover.stop(); cam_stream.release(); cv2.destroyAllWindows()
    eye_t.release(); hand_t.release()

if __name__ == "__main__":
    run()