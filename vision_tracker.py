"""
vision_tracker.py
- Nose tracking → cursor
- Hand gestures (clicks + DRAG support):
    LEFT PINCH   (Thumb + Index)  = LEFT click OR click-and-drag
    RIGHT PINCH  (Thumb + Pinky)  = RIGHT click
    TWO FINGERS  (Index + Middle) = Scroll Up/Down
"""
from __future__ import annotations
import time, urllib.request, os, logging, math
from dataclasses import dataclass, field
from typing import Optional
import cv2, mediapipe as mp, numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.vision import RunningMode

logger = logging.getLogger("GestureX")

FACE_URL   = ("https://storage.googleapis.com/mediapipe-models/"
              "face_landmarker/face_landmarker/float16/1/face_landmarker.task")
HAND_URL   = ("https://storage.googleapis.com/mediapipe-models/"
              "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task")
FACE_MODEL = "face_landmarker.task"
HAND_MODEL = "hand_landmarker.task"
CAL_FILE   = "cal_data.txt"

def _download_model(url, path):
    if not os.path.exists(path):
        print(f"Downloading {path} ...")
        urllib.request.urlretrieve(url, path)
        print(f"Done: {path}")

@dataclass
class VisionResult:
    cursor_x:     Optional[float] = None
    cursor_y:     Optional[float] = None
    left_click:   bool = False
    right_click:  bool = False
    double_click: bool = False
    mouse_down:   bool = False   
    mouse_up:     bool = False   
    dragging:     bool = False   
    scroll_dy:    int  = 0
    status:       str  = ""

class OneEuroFilter:
    def __init__(self, min_cutoff=0.5, beta=0.007):
        self.min_cutoff=min_cutoff; self.beta=beta
        self._x=None; self._dx=0.0; self._t=None; self.freq=30.0

    def _alpha(self, cutoff): return 1.0/(1.0+(1.0/(2*np.pi*cutoff))/(1.0/self.freq))

    def update(self, x):
        now=time.perf_counter()
        if self._x is None: self._x=x; self._t=now; return x
        dt=now-self._t
        if dt>0: self.freq=1.0/dt
        self._t=now
        dx=(x-self._x)*self.freq
        a_d=self._alpha(1.0)
        self._dx=a_d*dx+(1-a_d)*self._dx
        a=self._alpha(self.min_cutoff+self.beta*abs(self._dx))
        self._x=a*x+(1-a)*self._x
        return float(self._x)

    def reset(self): self._x=None; self._dx=0.0; self._t=None

class DeadZone:
    def __init__(self, threshold=0.0015): self.threshold=threshold; self._last=None
    def update(self, x):
        if self._last is None: self._last=x; return x
        if abs(x-self._last)>self.threshold: self._last=x
        return self._last
    def reset(self): self._last=None

FACE_ANCHORS=[1,4,6,168,197]
WRIST=0; THUMB_TIP=4; THUMB_MCP=2
INDEX_TIP=8;  INDEX_MCP=5;  INDEX_PIP=6
MIDDLE_TIP=12;MIDDLE_MCP=9; MIDDLE_PIP=10
RING_TIP=16;  RING_MCP=13;  RING_PIP=14
PINKY_TIP=20; PINKY_MCP=17; PINKY_PIP=18
HAND_CONNECTIONS=[
    (0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
    (5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),
    (13,17),(17,18),(18,19),(19,20),(0,17),
]

class CursorAccelerator:
    def __init__(self):
        self.last_t = time.perf_counter()
        self.last_x = None; self.last_y = None
        self.v_x = 0.5; self.v_y = 0.5 

    def update(self, abs_x, abs_y):
        now = time.perf_counter()
        dt = max(now - self.last_t, 0.001)
        self.last_t = now

        if self.last_x is None:
            self.last_x = abs_x; self.last_y = abs_y
            self.v_x = abs_x; self.v_y = abs_y
            return self.v_x, self.v_y

        dx = abs_x - self.last_x
        dy = abs_y - self.last_y
        self.last_x = abs_x; self.last_y = abs_y

        speed = math.hypot(dx, dy) / dt
        accel = 1.0 + min(2.0, (speed ** 1.2) * 0.8)

        self.v_x += dx * accel
        self.v_y += dy * accel
        self.v_x += (abs_x - self.v_x) * 0.04
        self.v_y += (abs_y - self.v_y) * 0.04
        self.v_x = max(-0.05, min(1.05, self.v_x))
        self.v_y = max(-0.05, min(1.05, self.v_y))

        return self.v_x, self.v_y

class EyeTracker:
    def __init__(self):
        _download_model(FACE_URL, FACE_MODEL)
        opts=mp_vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=FACE_MODEL),
            running_mode=RunningMode.IMAGE, num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.4,
            min_tracking_confidence=0.4,
        )
        self._det=mp_vision.FaceLandmarker.create_from_options(opts)
        self._accel = CursorAccelerator()
        self._fx=OneEuroFilter(min_cutoff=0.05, beta=0.02)
        self._fy=OneEuroFilter(min_cutoff=0.05, beta=0.02)
        self._dzx=DeadZone(0.004)
        self._dzy=DeadZone(0.004)
        
        self._x_min=0.30; self._x_max=0.70
        self._y_min=0.25; self._y_max=0.65
        self._ready=False; self._xs=[]; self._ys=[]
        self._warmup=60; self._frames=0
        self._last_sx=0.5; self._last_sy=0.5; self._lost_frames=0
        
        self.calibrating=False; self.cal_instruction=""
        self.cal_progress=0.0
        self._cal_active=False; self._cal_xs=[]; self._cal_ys=[]
        self._cal_start=0.0
        self._load_cal()

    def _save_cal(self):
        try:
            with open(CAL_FILE,"w") as f:
                f.write(f"{self._x_min}\n{self._x_max}\n{self._y_min}\n{self._y_max}\n")
        except Exception as e: pass

    def _load_cal(self):
        if not os.path.exists(CAL_FILE): return
        try:
            vals=[float(l.strip()) for l in open(CAL_FILE).readlines()]
            if len(vals)==4:
                self._x_min,self._x_max=vals[0],vals[1]
                self._y_min,self._y_max=vals[2],vals[3]
                self._ready=True
        except Exception as e: pass

    def start_calibration(self):
        self._cal_xs=[]; self._cal_ys=[]; self._cal_start=time.time()
        self._cal_active=True; self.calibrating=True; self._ready=False
        self.cal_progress = 0.0
        self._fx.reset(); self._fy.reset(); self._dzx.reset(); self._dzy.reset()
        self.cal_instruction="Calibrating Face bounds..."

    def _finish_cal(self):
        if len(self._cal_xs)>20:
            self._lock_range(self._cal_xs,self._cal_ys,pad=0.06)
            self._ready=True; self._save_cal()
        self._cal_active=False; self.calibrating=False; self.cal_instruction=""
        self.cal_progress = 0.0

    def _lock_range(self,xs,ys,pad=0.06):
        self._x_min=float(np.percentile(xs,5))-pad; self._x_max=float(np.percentile(xs,95))+pad
        self._y_min=float(np.percentile(ys,5))-pad; self._y_max=float(np.percentile(ys,95))+pad
        for mn,mx in[('_x_min','_x_max'),('_y_min','_y_max')]:
            lo,hi=getattr(self,mn),getattr(self,mx)
            if hi-lo<0.08:
                mid=(lo+hi)/2; setattr(self,mn,mid-0.04); setattr(self,mx,mid+0.04)

    SENSITIVITY = 1.2

    def _map(self,nx,ny):
        raw_cx = (nx - self._x_min) / max(self._x_max - self._x_min, 0.01)
        raw_cy = (ny - self._y_min) / max(self._y_max - self._y_min, 0.01)
        cx = 0.5 + (raw_cx - 0.5) * self.SENSITIVITY
        cy = 0.5 + (raw_cy - 0.5) * self.SENSITIVITY
        return cx, cy

    def process(self,frame):
        result=VisionResult(); h,w=frame.shape[:2]
        
        # --- LIGHTING NORMALIZATION ---
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l_channel)
        merged = cv2.merge((cl, a, b))
        balanced_frame = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        
        rgb = cv2.cvtColor(balanced_frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        det = self._det.detect(mp_img)
        # ------------------------------

        if not self.calibrating:
            x1, y1 = int(self._x_min * w), int(self._y_min * h)
            x2, y2 = int(self._x_max * w), int(self._y_max * h)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (100, 100, 100), 1)
            cv2.putText(frame, "[C] FACE BOUNDS", (x1 + 5, y1 + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1, cv2.LINE_AA)

        if not det.face_landmarks:
            self._lost_frames+=1
            if self._lost_frames<10 and self._ready:
                result.cursor_x=self._last_sx; result.cursor_y=self._last_sy
                result.status="Face: searching..."
            else:
                self._fx.reset(); self._fy.reset(); self._dzx.reset(); self._dzy.reset()
                result.status="Face: not detected"
            return result
            
        self._lost_frames=0
        lm=det.face_landmarks[0]
        raw_x=float(np.mean([lm[i].x for i in FACE_ANCHORS]))
        raw_y=float(np.mean([lm[i].y for i in FACE_ANCHORS]))
        self._frames+=1
        
        if self._cal_active:
            self._cal_xs.append(raw_x); self._cal_ys.append(raw_y)
            elapsed=time.time()-self._cal_start
            self.cal_progress = min(1.0, elapsed / 5.0)
            if elapsed>=5.0: self._finish_cal()
        else:
            if not self._ready:
                self._xs.append(raw_x); self._ys.append(raw_y)
                if self._frames>=self._warmup:
                    self._lock_range(self._xs,self._ys,pad=0.02); self._ready=True
                    
        if not self._ready:
            result.status="Warming up..."
            return result
            
        abs_x, abs_y = self._map(raw_x, raw_y)
        ax, ay = self._accel.update(abs_x, abs_y)
        
        sx=self._dzx.update(self._fx.update(ax))
        sy=self._dzy.update(self._fy.update(ay))
        
        self._last_sx=sx; self._last_sy=sy
        result.cursor_x=sx; result.cursor_y=sy
        result.status=f"Face active"
        return result

    def release(self): self._det.close()

# ── Hand gesture detection ─────────────────────────────────────────────────────
CONFIRM_FRAMES  = 4     
RELEASE_FRAMES  = 3     
DRAG_HOLD_SEC   = 0.35  

def _dist2d(a, b): return np.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)

def _detect_left_pinch(lm):
    hand_size = _dist2d(lm[WRIST], lm[MIDDLE_MCP]) + 1e-6
    tip_dist  = _dist2d(lm[THUMB_TIP], lm[INDEX_TIP])
    return (tip_dist / hand_size) < 0.25

def _detect_right_pinch(lm):
    hand_size = _dist2d(lm[WRIST], lm[MIDDLE_MCP]) + 1e-6
    tip_dist  = _dist2d(lm[THUMB_TIP], lm[PINKY_TIP])
    return (tip_dist / hand_size) < 0.28 

# NEW: Highly robust Two-Finger Scroll logic
def _detect_two_finger_scroll(lm):
    def d(a,b): return _dist2d(lm[a], lm[b])
    
    # Check if the tip of the finger is significantly further from the wrist than the knuckle (extended)
    index_up  = d(WRIST, INDEX_TIP) > d(WRIST, INDEX_MCP) * 1.2
    middle_up = d(WRIST, MIDDLE_TIP) > d(WRIST, MIDDLE_MCP) * 1.2
    # Check if ring and pinky are curled inward
    ring_down  = d(WRIST, RING_TIP) < d(WRIST, RING_MCP) * 1.2
    pinky_down = d(WRIST, PINKY_TIP) < d(WRIST, PINKY_MCP) * 1.2
    
    return index_up and middle_up and ring_down and pinky_down

HAND_CAL_FILE = "hand_cal_data.txt"

class HandTracker:
    def __init__(self):
        _download_model(HAND_URL, HAND_MODEL)
        opts=mp_vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=HAND_MODEL),
            running_mode=RunningMode.IMAGE, num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.4,
            min_tracking_confidence=0.4,
        )
        self._det=mp_vision.HandLandmarker.create_from_options(opts)

        self._pinch_count   = 0; self._pinch_release = 0     
        self._pinch_held    = False; self._pinch_start   = 0.0  
        self._dragging      = False 
        
        self._right_count   = 0; self._right_release = 0     
        self._right_active  = False
        
        # Scroll State
        self._scrolling     = False
        self._last_scroll_y = 0.0

        self._last_label    = "none"

        self._cx = OneEuroFilter(min_cutoff=0.15, beta=0.06)
        self._cy = OneEuroFilter(min_cutoff=0.15, beta=0.06)
        
        self._x_min = 0.30; self._x_max = 0.70
        self._y_min = 0.30; self._y_max = 0.70
        self.SENSITIVITY = 1.0   

        self.calibrating = False; self.cal_instruction = ""
        self.cal_progress = 0.0
        self._cal_active = False; self._cal_xs = []; self._cal_ys = []
        self._cal_start  = 0.0
        self._load_cal()

    def _save_cal(self):
        try:
            with open(HAND_CAL_FILE, "w") as f:
                f.write(f"{self._x_min}\n{self._x_max}\n{self._y_min}\n{self._y_max}\n")
        except: pass

    def _load_cal(self):
        if not os.path.exists(HAND_CAL_FILE): return
        try:
            vals = [float(l.strip()) for l in open(HAND_CAL_FILE).readlines()]
            if len(vals) == 4:
                self._x_min, self._x_max = vals[0], vals[1]
                self._y_min, self._y_max = vals[2], vals[3]
        except: pass

    def start_calibration(self):
        self._cal_xs = []; self._cal_ys = []; self._cal_start = time.time()
        self._cal_active = True; self.calibrating = True
        self.cal_progress = 0.0
        self._cx.reset(); self._cy.reset()
        self.cal_instruction = "Calibrating Hand tracking zone..."

    def _finish_cal(self):
        if len(self._cal_xs) > 20:
            pad = 0.04
            self._x_min = float(np.percentile(self._cal_xs,  5)) - pad; self._x_max = float(np.percentile(self._cal_xs, 95)) + pad
            self._y_min = float(np.percentile(self._cal_ys,  5)) - pad; self._y_max = float(np.percentile(self._cal_ys, 95)) + pad
            for mn, mx in [('_x_min','_x_max'), ('_y_min','_y_max')]:
                lo, hi = getattr(self, mn), getattr(self, mx)
                if hi - lo < 0.08:
                    mid = (lo+hi)/2; setattr(self, mn, mid-0.04); setattr(self, mx, mid+0.04)
            self._save_cal()
        self._cal_active = False; self.calibrating = False; self.cal_instruction = ""
        self.cal_progress = 0.0

    def _map(self, px, py):
        raw_x = (px - self._x_min) / max(self._x_max - self._x_min, 0.01)
        raw_y = (py - self._y_min) / max(self._y_max - self._y_min, 0.01)
        sx = 0.5 + (raw_x - 0.5) * self.SENSITIVITY
        sy = 0.5 + (raw_y - 0.5) * self.SENSITIVITY
        return float(np.clip(sx, -0.05, 1.05)), float(np.clip(sy, -0.05, 1.05))

    def process(self, frame: np.ndarray, hand_cursor=False) -> VisionResult:
        result=VisionResult(); h,w=frame.shape[:2]
        rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        mp_img=mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb)
        det=self._det.detect(mp_img)

        if hand_cursor and not self.calibrating:
            x1, y1 = int(self._x_min * w), int(self._y_min * h)
            x2, y2 = int(self._x_max * w), int(self._y_max * h)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (100, 100, 100), 1)
            cv2.putText(frame, "[H] HAND ZONE", (x1 + 5, y1 + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1, cv2.LINE_AA)

        if not det.hand_landmarks:
            self._cx.reset(); self._cy.reset()
            if self._dragging:
                result.mouse_up  = True; self._dragging = False
            self._pinch_count = 0; self._pinch_release = 0; self._pinch_held = False
            self._right_count = 0; self._right_release = 0; self._right_active = False
            self._scrolling = False
            result.status = "Hand: not detected"; self._last_label = "none"
            return result

        lm = det.hand_landmarks[0]
        palm_x = float((lm[WRIST].x * 0.7) + (lm[MIDDLE_MCP].x * 0.3))
        palm_y = float((lm[WRIST].y * 0.7) + (lm[MIDDLE_MCP].y * 0.3))

        if self._cal_active:
            self._cal_xs.append(palm_x); self._cal_ys.append(palm_y)
            elapsed = time.time() - self._cal_start
            self.cal_progress = min(1.0, elapsed / 5.0)
            if elapsed >= 5.0: self._finish_cal()

        left_pinch  = _detect_left_pinch(lm)
        right_pinch = _detect_right_pinch(lm)
        two_finger  = _detect_two_finger_scroll(lm)

        if hand_cursor and not two_finger:
            raw_sx, raw_sy = self._map(palm_x, palm_y)
            sx = self._cx.update(raw_sx); sy = self._cy.update(raw_sy)
            result.cursor_x = sx; result.cursor_y = sy

        # NEW: Scroll Logic
        if two_finger:
            self._pinch_held = False; self._dragging = False 
            if not self._scrolling:
                self._scrolling = True
                self._last_scroll_y = palm_y
            else:
                dy = palm_y - self._last_scroll_y
                if abs(dy) > 0.005: # Noise threshold
                    # Convert physical hand movement into scroll wheel ticks
                    result.scroll_dy = int(dy * 8000) 
                    self._last_scroll_y = palm_y
            self._last_label = "SCROLL"
            
        else:
            self._scrolling = False
            
            if left_pinch and not right_pinch:
                self._pinch_release = 0          
                if self._pinch_count < CONFIRM_FRAMES: self._pinch_count += 1
                if self._pinch_count >= CONFIRM_FRAMES:
                    if not self._pinch_held:
                        self._pinch_held = True; self._pinch_start = time.time(); self._dragging = False
                    else:
                        held_for = time.time() - self._pinch_start
                        if not self._dragging and held_for >= DRAG_HOLD_SEC:
                            result.mouse_down = True; self._dragging = True
            else:
                self._pinch_release += 1
                if self._pinch_release >= RELEASE_FRAMES:
                    if self._dragging:
                        result.mouse_up = True; self._dragging = False
                    elif self._pinch_held:
                        result.left_click = True
                    self._pinch_count = 0; self._pinch_held = False; self._pinch_release = 0

            if self._dragging: result.dragging = True

            if right_pinch and not left_pinch:
                self._right_release = 0
                if self._right_count < CONFIRM_FRAMES: self._right_count += 1
                if self._right_count >= CONFIRM_FRAMES and not self._right_active:
                    result.right_click = True; self._right_active = True
            else:
                self._right_release += 1
                if self._right_release >= RELEASE_FRAMES:
                    self._right_count = 0; self._right_active = False; self._right_release = 0

            if self._dragging:              self._last_label = "DRAGGING"
            elif left_pinch and self._pinch_held:self._last_label = "L-Hold"
            elif left_pinch:                self._last_label = "L-Pinch"
            elif right_pinch:               self._last_label = "R-CLICK"
            else:                           self._last_label = "Open"

        result.status = f"Hand|{self._last_label}"

        pts = [(int(lm[i].x*w),int(lm[i].y*h)) for i in range(21)]
        for a,b in HAND_CONNECTIONS: cv2.line(frame,pts[a],pts[b],(180,140,0),1)
        
        # Color the fingers depending on if they are scrolling or not
        for i,pt in enumerate(pts):
            col = (0,255,80) if (two_finger and i in (INDEX_TIP, MIDDLE_TIP)) else ((0,255,80) if (not two_finger and i in (THUMB_TIP,INDEX_TIP,PINKY_TIP)) else (0,190,255))
            cv2.circle(frame,pt,4,col,-1)

        if hand_cursor and not two_finger:
            pcx = int(palm_x * w); pcy = int(palm_y * h)
            cv2.circle(frame, (pcx,pcy), 10, (0,255,200), 2)
            cv2.drawMarker(frame, (pcx,pcy), (0,255,200), cv2.MARKER_CROSS, 16, 2)

        if self._pinch_held: cv2.putText(frame,"HOLDING",(10,80),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,200,255),2)
        if two_finger: cv2.putText(frame,"SCROLLING",(10,80),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,80),2)
        
        return result

    @property
    def gesture(self): return self._last_label

    def release(self): self._det.close()