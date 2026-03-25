"""
state_manager.py - Thread-safe shared state hub.
"""
import threading, time

class AppState:
    def __init__(self):
        self._lock = threading.Lock()
        self.active_controller: str = "none"
        self.last_move_time: dict = {"eye": 0.0, "hand": 0.0}
        self.controller_timeout: float = 1.5
        self.voice_active: bool = True
        self.pending_text: str = ""
        self.pending_command: str = ""
        self.running: bool = True
        self.debug: bool = False

    def set(self, key, value):
        with self._lock: setattr(self, key, value)

    def get(self, key):
        with self._lock: return getattr(self, key)

    def request_control(self, source):
        with self._lock:
            now = time.time()
            current = self.active_controller
            if current == "none":
                self.active_controller = source
                self.last_move_time[source] = now
                return True
            if current == source:
                self.last_move_time[source] = now
                return True
            elapsed = now - self.last_move_time.get(current, 0.0)
            if elapsed > self.controller_timeout:
                self.active_controller = source
                self.last_move_time[source] = now
                return True
            return False

    def release_control(self, source):
        with self._lock:
            if self.active_controller == source:
                self.active_controller = "none"

    def consume_pending_text(self):
        with self._lock:
            t = self.pending_text; self.pending_text = ""; return t

    def consume_pending_command(self):
        with self._lock:
            c = self.pending_command; self.pending_command = ""; return c

app_state = AppState()
