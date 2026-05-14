"""
gesture_controller.py - Maps gestures to media actions.
Looks up keys from available_actions (not the gesture entry).
Only sends keystrokes when a recognized media window is focused.
"""
import pyautogui
import time
import threading
from config_manager import get_gesture_mappings, get_available_actions, get_settings

try:
    import pygetwindow as gw
    HAS_GETWINDOW = True
except ImportError:
    HAS_GETWINDOW = False

pyautogui.PAUSE = 0.03
pyautogui.FAILSAFE = True


class GestureController:
    def __init__(self):
        self.gesture_mappings = get_gesture_mappings()
        self.available_actions = get_available_actions()
        self._load_settings()
        self.action_log = []
        self.max_log_size = 30
        self._lock = threading.Lock()
        self._space_held = False

    def _load_settings(self):
        settings = get_settings()
        self.target_windows = [w.lower() for w in settings.get("target_windows", [])]
        self.window_filter_enabled = settings.get("window_filter_enabled", True)

    def reload_mappings(self):
        self.gesture_mappings = get_gesture_mappings()
        self.available_actions = get_available_actions()
        self._load_settings()

    def _is_target_window_active(self):
        """Returns True if the focused window is a media player (or filter is off)."""
        if not self.window_filter_enabled:
            return True
        if not HAS_GETWINDOW:
            return True  # Can't check, allow all
        try:
            win = gw.getActiveWindow()
            if win is None:
                return False
            title = win.title.lower()
            return any(kw in title for kw in self.target_windows)
        except Exception:
            return True  # If check fails, allow the action

    def execute(self, gesture_name):
        mapping = self.gesture_mappings.get(gesture_name)
        if not mapping:
            return None
        action = mapping.get("action", "none")
        description = mapping.get("description", "")
        if action == "none" or action == "speed_2x":
            return None  # speed_2x handled by handle_hold

        if not self._is_target_window_active():
            print(f"[Controller] Blocked: {action} — media window not focused")
            return None

        try:
            self._do_action(action)
        except Exception as e:
            print(f"[Controller] Error executing {action}: {e}")
            return None

        entry = {
            "gesture": gesture_name, "action": action,
            "description": description,
            "timestamp": time.strftime("%H:%M:%S"), "time": time.time(),
        }
        with self._lock:
            self.action_log.insert(0, entry)
            if len(self.action_log) > self.max_log_size:
                self.action_log = self.action_log[:self.max_log_size]

        print(f"[Controller] Triggered: {gesture_name} -> {action} ({description})")
        return entry

    def handle_hold(self, gesture_name):
        """Holds spacebar while peace (2 fingers) is detected — YouTube 2x."""
        peace_action = self.gesture_mappings.get("peace", {}).get("action", "")
        wants_hold = (gesture_name == "peace" and peace_action == "speed_2x")
        if wants_hold and not self._space_held:
            if not self._is_target_window_active():
                return
            pyautogui.keyDown("space")
            self._space_held = True
            self._log("peace", "speed_2x", "Speed 2x (holding)")
        elif not wants_hold and self._space_held:
            pyautogui.keyUp("space")
            self._space_held = False

    def release_all(self):
        if self._space_held:
            pyautogui.keyUp("space")
            self._space_held = False

    def _do_action(self, action):
        """Look up keys from available_actions and press them."""
        action_config = self.available_actions.get(action, {})
        keys = action_config.get("keys", [])
        if not keys:
            print(f"  -> No keys configured for action [{action}]")
            return
        for k in keys:
            pyautogui.press(k)
            print(f"  -> Pressed [{k}]")
            time.sleep(0.05)

    def _log(self, gesture, action, description):
        entry = {"gesture": gesture, "action": action, "description": description,
                 "timestamp": time.strftime("%H:%M:%S"), "time": time.time()}
        with self._lock:
            self.action_log.insert(0, entry)
            if len(self.action_log) > self.max_log_size:
                self.action_log = self.action_log[:self.max_log_size]

    def get_recent_actions(self, count=10):
        with self._lock:
            return self.action_log[:count]

    def clear_log(self):
        with self._lock:
            self.action_log.clear()
