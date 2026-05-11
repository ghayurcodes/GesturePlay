# GesturePlay — Developer Guide

Quick reference for running, understanding, and modifying the project.

---

## Quick Start

```bash
# Install dependencies (first time only)
pip install opencv-python mediapipe flask pyautogui

# Start the app
python app.py

# Open in browser
http://localhost:5000
```

---

## File Structure

```
Dip project/
├── app.py                    Main Flask server
├── gesture_detector.py       Hand detection + gesture classification
├── gesture_controller.py     Keyboard action executor
├── config_manager.py         Load/save gesture_config.json
├── gesture_config.json       Gesture-to-action mappings (edit here)
├── requirements.txt          Python dependencies
├── templates/
│   └── index.html            Web UI page
└── static/
    ├── css/style.css         UI styling (dark gray/silver theme)
    └── js/app.js             Frontend logic
```

---

## File Descriptions

### `app.py` — Flask Server
The main entry point. Run this to start everything.

**What it does:**
- Starts a Flask web server at `http://localhost:5000`
- Starts the detection loop in a background thread when you click "Start"
- Streams the annotated webcam feed as MJPEG via `/video_feed`
- Exposes REST API endpoints:
  - `GET  /`              → Serves the web UI
  - `GET  /video_feed`    → MJPEG camera stream
  - `GET  /api/status`    → Current gesture, FPS, recent actions
  - `POST /api/toggle`    → Start or stop detection
  - `GET  /api/config`    → Get gesture mappings
  - `POST /api/config`    → Update a gesture mapping

**Performance trick:** Uses `deque(maxlen=1)` to share frames between the capture thread and the streaming generator — zero-wait, always fresh.

---

### `gesture_detector.py` — Hand Detection
Uses MediaPipe to detect hands and classify gestures.

**What it does:**
- Opens the webcam, processes each frame through MediaPipe Hands
- Draws the hand skeleton on the frame
- Counts raised fingers (excluding thumb) to classify gestures
- Applies an **8-frame stability buffer** — a gesture must appear in 65%+ of recent frames before it's considered confirmed
- Enforces **per-gesture hold thresholds** (0.25s–0.80s)
- Enforces a **neutral gap** after every trigger — no new gesture fires until the hand is absent for 0.6s

**To tune sensitivity:**
```python
# In gesture_detector.py, top of file
HOLD_THRESHOLDS = {
    "fist":      0.80,   # increase if too sensitive
    "index_up":  0.45,
    "peace":     0.25,
    "three_up":  0.45,
    "open_palm": 0.55,
}

# In __init__
self.neutral_gap  = 0.60   # seconds to wait after trigger
self.STABLE_RATIO = 0.65   # % of buffer that must agree (0.0–1.0)
```

---

### `gesture_controller.py` — Action Executor
Maps gesture names to keyboard actions and executes them via PyAutoGUI.

**What it does:**
- `execute(gesture_name)` — looks up the gesture in config and fires the action
- `handle_hold(gesture_name)` — called every frame; holds spacebar while ✌️ peace is detected (YouTube 2x speed)
- `release_all()` — releases spacebar when detection stops

**To add a new action type**, add a new `elif action == "your_action":` block in `_do_action()`.

**Key design choice:** Play/Pause is a simple spacebar toggle — no state tracking. This avoids sync issues if the user manually pauses/plays.

---

### `config_manager.py` — Configuration
Loads and saves `gesture_config.json`. Called by the controller and the Flask API.

**Key functions:**
- `load_config()` — reads the JSON file (UTF-8)
- `save_config(config)` — writes back to JSON
- `update_gesture_action(gesture, action)` — remaps one gesture at runtime
- `get_gesture_mappings()` — returns just the gestures dict

---

### `gesture_config.json` — Gesture Mappings
The single source of truth for all gesture-to-action mappings. Edited at runtime via the web UI or directly.

**Structure:**
```json
{
  "gestures": {
    "fist":      { "action": "play_pause", ... },
    "index_up":  { "action": "skip_bwd",  ... },
    "peace":     { "action": "speed_2x",  ... },
    "three_up":  { "action": "skip_fwd",  ... },
    "open_palm": { "action": "mute",      ... }
  },
  "available_actions": { ... },
  "settings": { ... }
}
```

**To change a gesture action:** Either use the web UI dropdown, or edit this file directly and restart the server.

---

### `templates/index.html` — Web UI Page
Single-page layout with:
- Live camera feed panel (left)
- Gesture readout with 5 finger-count dots (below camera)
- Gesture Map panel with dropdowns (right)
- Action Log (right)
- How To Use instructions (right)

---

### `static/css/style.css` — Styling
Dark gray / silver theme. All colors defined as CSS variables at the top:
```css
:root {
    --bg: #141414;
    --surface: #1e1e1e;
    --silver: #b0b0b0;
    --silver-hi: #d4d4d4;
    ...
}
```

---

### `static/js/app.js` — Frontend Logic
- `toggleDetection()` — calls `/api/toggle`, shows/hides camera feed
- `pollStatus()` — runs every 400ms, updates gesture display, FPS, log
- `loadConfig()` — fetches gesture mappings, renders the config table
- `saveMapping(gesture, action)` — POSTs a config change to the server
- `toast(msg, type)` — shows a temporary notification

---

## Default Gesture Map

| Emoji | Gesture | Fingers | Action | Keys Sent |
|-------|---------|---------|--------|-----------|
| ✊ | Fist | 0 | Play / Pause Toggle | `Space` |
| ☝️ | One Finger | 1 | Skip Backward 10s | `← ←` (×2) |
| ✌️ | Two Fingers | 2 | Speed 2x (hold) | Hold `Space` |
| 🤟 | Three Fingers | 3 | Skip Forward 10s | `→ →` (×2) |
| ✋ | Open Palm | 4 | Mute / Unmute | `M` |

---

## How to Use

1. Run `python app.py`
2. Open `http://localhost:5000` in Chrome
3. Click **Start Detection**
4. Open YouTube or a media player in another window
5. **Click on the media player** to focus it (keys go to the active window)
6. Show gestures to your webcam
7. After each gesture fires, **lower your hand briefly** (0.6s) to unlock the next gesture

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Camera not opening | Another app is using the webcam — close it |
| Gestures not triggering | Hard-refresh the browser (`Ctrl+Shift+R`) |
| Play/Pause going to browser | Click on the YouTube video player first |
| Gestures firing randomly | Lower your hand between gestures (neutral gap) |
| Low FPS | Close other heavy applications; reduce camera resolution in `app.py` |
| Config not loading | Check `gesture_config.json` for syntax errors |

---
