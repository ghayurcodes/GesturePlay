# GesturePlay — Project Report

**Course:** Digital Image Processing  
**Project Title:** Real-Time Hand Gesture-Controlled Media Player  
**Technology Stack:** Python, OpenCV, MediaPipe, Flask, PyAutoGUI

---

## 1. Introduction

  GesturePlay is a real-time, computer-vision-based system that enables users to control media playback on their laptop using only hand gestures captured through the built-in webcam.

The system runs entirely locally on the user's machine. A lightweight Flask web application serves as the control dashboard, providing a live annotated camera feed and a customizable gesture configuration panel.

---
## 2. Problem Statement

Modern media consumption often involves watching content from a distance (e.g., lying on a bed, sitting across the room). Reaching for the keyboard every time to pause, skip, or adjust volume is inconvenient. A touchless, gesture-based remote control that leverages existing hardware (a laptop webcam) solves this problem without requiring any additional devices.

---

## 3. Objectives

- Detect and classify hand gestures in real time using the laptop webcam
- Map detected gestures to media control actions (play/pause, seek, speed, mute)
- Deliver a stable, responsive system with minimal false triggers
- Provide a web-based UI for live monitoring and gesture customization
- Work with YouTube (Chrome) and Windows Media Player without any browser extensions

---

## 4. System Architecture

```
Webcam
  │
  ▼
OpenCV (Frame Capture)
  │
  ▼
MediaPipe Hands (21-landmark skeleton)
  │
  ▼
Gesture Detector (finger counting + stability buffer)
  │
  ▼
Gesture Controller (action mapping + spacebar hold)
  │
  ▼
PyAutoGUI (keyboard shortcuts → active window)
  │
  ▼
YouTube / Windows Media Player
```

A Flask web server runs in parallel, streaming the annotated webcam feed as MJPEG and exposing REST API endpoints for the web UI.

---

## 5. Technology Stack

| Component | Library / Tool | Version | Purpose |
|-----------|---------------|---------|---------|
| Hand Tracking | MediaPipe | 0.10.x | 21-point hand landmark detection |
| Computer Vision | OpenCV | 4.10.x | Webcam capture, frame annotation |
| Keyboard Control | PyAutoGUI | 0.9.x | Sending keystrokes to active window |
| Web Server | Flask | 3.1.x | Serving UI and REST API |
| Frontend | HTML/CSS/JavaScript | — | Dashboard and gesture config panel |

---

## 6. Hand Gesture Detection Methodology

### 6.1 MediaPipe Hand Landmarks

MediaPipe Hands detects 21 3D landmarks on a hand in real time. The system uses only the 2D (x, y pixel) positions of these landmarks.

```
Landmark IDs used:
  4  = Thumb tip
  8  = Index fingertip
  12 = Middle fingertip
  16 = Ring fingertip
  20 = Pinky fingertip

  6  = Index PIP joint
  10 = Middle PIP joint
  14 = Ring PIP joint
  18 = Pinky PIP joint
```

### 6.2 Finger State Detection

A finger is considered **raised** if its tip's Y-coordinate is less than its PIP joint's Y-coordinate (since Y increases downward in image space):

```
finger_up = tip.y < pip.y
```

The thumb is excluded from counting for simplicity and reliability, as its detection is less consistent due to its horizontal orientation.

### 6.3 Gesture Classification

Gestures are classified purely by the count of raised fingers (0–4):

| Finger Count | Gesture Name | Default Action |
|-------------|-------------|----------------|
| 0 | Fist | Play / Pause Toggle |
| 1 | One Finger | Skip Backward 10s |
| 2 | Peace Sign | Speed 2x (hold) |
| 3 | Three Fingers | Skip Forward 10s |
| 4 | Open Palm | Mute / Unmute |

### 6.4 Stability Buffer (Anti-Flicker)

A key reliability improvement is the **8-frame rolling stability buffer**. Raw gesture detections for the last 8 frames are stored in a `collections.deque`. A gesture is only considered confirmed when it appears in **65% or more** of the buffer:

```python
threshold = 8 * 0.65 = 5.2 frames
```

This eliminates single-frame false detections caused by hand rotation, partial occlusion, or lighting changes.

### 6.5 Neutral-Gap Gating

After any gesture triggers an action, the system enters a **neutral-gap state**. No new gesture can fire until the hand is absent from the frame for at least **0.6 seconds**. This prevents transition-state false triggers — for example, moving from a fist to an open palm briefly passing through 1, 2, and 3 fingers on the way.

### 6.6 Per-Gesture Hold Thresholds

Each gesture requires a minimum hold duration before it fires:

| Gesture | Hold Required | Rationale |
|---------|------------|-----------|
| Fist | 0.80s | Most impactful action — prevent accidents |
| One Finger | 0.45s | Moderate |
| Peace Sign | 0.25s | Fast for hold-based 2x speed |
| Three Fingers | 0.45s | Moderate |
| Open Palm | 0.55s | Prevent accidental mute |

---

## 7. Speed Control (2x) — Hold Mechanism

YouTube plays at 2x speed while the spacebar is held down. The system exploits this by using `pyautogui.keyDown("space")` when the peace gesture is detected, and `pyautogui.keyUp("space")` when the gesture changes. This provides smooth, continuous speed control that is tied directly to the gesture duration.

---

## 8. Seek Control

Skip backward and skip forward use **double arrow key presses**:
- Skip Backward: `Left Arrow` × 2 (each press = 5s back → total 10s)
- Skip Forward: `Right Arrow` × 2 (each press = 5s forward → total 10s)

This works universally on YouTube and Windows Media Player.

---

## 9. Web Dashboard

The Flask web application provides:

1. **Live Camera Feed** — MJPEG stream of the annotated webcam view, showing hand landmarks, detected gesture label, finger count, and FPS
2. **Gesture Readout** — Displays current detected gesture with emoji and 5 finger-count indicator dots
3. **Gesture Map Panel** — Dropdown selectors to remap any gesture to any action
4. **Action Log** — Real-time log of triggered actions with timestamps
5. **Start / Stop Toggle** — Enable or disable detection with one click

The UI uses a dark gray/silver theme and polls the `/api/status` endpoint every 400ms for live updates.

---

## 10. Performance Optimizations

| Optimization | Implementation |
|-------------|---------------|
| Lightweight model | MediaPipe `model_complexity=0` (lite model) |
| Camera buffer | `CAP_PROP_BUFFERSIZE=1` — always gets latest frame |
| Zero-wait streaming | `deque(maxlen=1)` between capture and MJPEG generator |
| JPEG quality | Encoded at quality 75 — fast but visually acceptable |
| Frame rate | Camera set to 640×480 @ 30fps |

---

## 11. Gesture Configuration

All gesture-to-action mappings are stored in `gesture_config.json`. Users can remap gestures at runtime via the web UI without restarting the server. Available actions include: Play/Pause, Speed 2x, Skip Forward, Skip Backward, Volume Up, Volume Down, Fullscreen, Mute, and No Action.

---

## 12. Limitations and Future Work

- **Lighting dependency** — Detection accuracy degrades in very low light
- **Single hand** — Currently tracks only one hand at a time
- **Angle sensitivity** — Extreme hand angles (>60° tilt) may cause misclassification
- **Active window dependency** — PyAutoGUI sends keys to the focused window; the media player must be in focus

**Future improvements:**
- Two-hand gesture support for richer command vocabulary
- Custom gesture training using hand landmark coordinates as features
- Browser extension integration to eliminate active-window constraint
- Volume control via hand height (raise/lower hand to adjust volume)

---

## 13. Conclusion

GesturePlay demonstrates a practical application of digital image processing and computer vision for human-computer interaction. By combining MediaPipe's real-time hand tracking with a robust gesture stability pipeline and a clean web interface, the system provides a reliable, touchless media controller that works with everyday streaming platforms and media players.

---
