"""
gesture_controller.py - Maps gestures to media actions.
play_pause is now a simple spacebar toggle - no state tracking.
"""
import pyautogui
import time
import threading
from config_manager import get_gesture_mappings

pyautogui.PAUSE = 0.03
pyautogui.FAILSAFE = True

class GestureController:
    def __init__(self):
        self.gesture_mappings = get_gesture_mappings()
        self.action_log = []
        self.max_log_size = 30
        self._lock = threading.Lock()
        self._space_held = False

    def reload_mappings(self):
        self.gesture_mappings = get_gesture_mappings()

    def execute(self, gesture_name):
        mapping = self.gesture_mappings.get(gesture_name)
        if not mapping:
            return None
        action = mapping.get("action", "none")
        description = mapping.get("description", "")
        if action == "none" or action == "speed_2x":
            return None  # speed_2x handled by handle_hold
        try:
            self._do_action(action, mapping)
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

    def _do_action(self, action, mapping):
        if action == "play_pause":
            pyautogui.press("space")
            print("  -> Pressed [space]")
        elif action == "mute":
            pyautogui.press("m")
            print("  -> Pressed [m]")
        elif action == "fullscreen":
            pyautogui.press("f")
            print("  -> Pressed [f]")
        else:
            keys = mapping.get("keys", [])
            if not keys:
                return
            # Press each key sequentially (handles double arrow presses)
            for k in keys:
                pyautogui.press(k)
                print(f"  -> Pressed [{k}]")
                time.sleep(0.1)

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
