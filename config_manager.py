"""
config_manager.py -- Load, save, and update gesture configuration.
"""

import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gesture_config.json")


def load_config():
    """Load gesture config from JSON."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return _default_config()


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def get_gesture_mappings():
    return load_config().get("gestures", {})


def get_available_actions():
    return load_config().get("available_actions", {})


def get_settings():
    return load_config().get("settings", {})


def update_gesture_action(gesture_name, action_name):
    """Remap a gesture to a new action. Returns True or error string."""
    config   = load_config()
    gestures = config.get("gestures", {})
    actions  = config.get("available_actions", {})

    if gesture_name not in gestures:
        return f"Unknown gesture: {gesture_name}"
    if action_name not in actions:
        return f"Unknown action: {action_name}"

    gestures[gesture_name]["action"]      = action_name
    gestures[gesture_name]["description"] = actions[action_name]["label"]
    config["gestures"] = gestures
    save_config(config)
    return True


def update_settings(new_settings):
    config = load_config()
    config.setdefault("settings", {}).update(new_settings)
    save_config(config)
    return True


def _default_config():
    return {
        "gestures": {
            "fist":      {"label": "Fist",          "emoji": "\u270a",     "fingers": "0 fingers", "action": "pause",    "description": "Pause"},
            "index_up":  {"label": "One Finger",    "emoji": "\u261d\ufe0f", "fingers": "1 finger",  "action": "skip_bwd", "description": "Skip Backward 10s"},
            "peace":     {"label": "Two Fingers",   "emoji": "\u270c\ufe0f", "fingers": "2 fingers", "action": "speed_2x", "description": "Speed 2x"},
            "three_up":  {"label": "Three Fingers", "emoji": "\ud83e\udd1f", "fingers": "3 fingers", "action": "skip_fwd", "description": "Skip Forward 10s"},
            "open_palm": {"label": "Open Palm",     "emoji": "\u270b",     "fingers": "4 fingers", "action": "play",     "description": "Play"},
        },
        "available_actions": {
            "play":       {"label": "Play",              "keys": ["k"]},
            "pause":      {"label": "Pause",             "keys": ["k"]},
            "speed_2x":   {"label": "Speed 2x (hold)",   "keys": ["speed_2x"]},
            "skip_fwd":   {"label": "Skip Forward 10s",  "keys": ["l"]},
            "skip_bwd":   {"label": "Skip Backward 10s", "keys": ["j"]},
            "vol_up":     {"label": "Volume Up",         "keys": ["up"]},
            "vol_down":   {"label": "Volume Down",       "keys": ["down"]},
            "fullscreen": {"label": "Fullscreen",        "keys": ["f"]},
            "mute":       {"label": "Mute",              "keys": ["m"]},
            "none":       {"label": "No Action",         "keys": []},
        },
        "settings": {
            "cooldown_seconds":      1.2,
            "detection_confidence":  0.8,
            "tracking_confidence":   0.5,
        },
    }
