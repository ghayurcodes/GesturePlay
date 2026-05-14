# -*- coding: utf-8 -*-
"""
app.py -- GesturePlay Flask Application

Serves the web dashboard, streams the annotated webcam feed as MJPEG,
and exposes REST API endpoints for gesture configuration and status.
Uses a deque(maxlen=1) for zero-wait frame sharing between threads.
"""

import cv2
import time
import threading
from collections import deque
from flask import Flask, Response, render_template, request, jsonify

from gesture_detector import GestureDetector
from gesture_controller import GestureController
from config_manager import load_config, update_gesture_action

# ─── Flask App ────────────────────────────────────────────────────────────────

app = Flask(__name__)

# ─── Global State ─────────────────────────────────────────────────────────────

detector = None
controller = None
detection_active = False
detection_thread = None

# deque(maxlen=1): producer always overwrites, consumer always gets latest
frame_queue = deque(maxlen=1)

current_status = {
    "gesture": None,
    "action": None,
    "description": None,
    "fps": 0,
    "active": False,
    "finger_count": 0,
}
status_lock = threading.Lock()


# ─── Detection Loop ───────────────────────────────────────────────────────────

def detection_loop():
    """
    Capture + detect in one tight loop.
    Uses CAP_PROP_BUFFERSIZE=1 to minimize camera lag (same trick as reference code).
    """
    global detector, controller, detection_active, current_status

    detector = GestureDetector(
        detection_confidence=0.7,
        tracking_confidence=0.5,
    )
    controller = GestureController()
    detector.set_action_labels(controller.gesture_mappings)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[GesturePlay] ERROR: Cannot open webcam.")
        detection_active = False
        return

    # Performance settings -- keeps camera buffer minimal
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)

    print("[GesturePlay] Camera opened. Detection running...")

    while detection_active:
        success, frame = cap.read()
        if not success:
            continue

        # Detect gesture
        gesture_name, annotated, finger_count = detector.detect(frame)

        # Push latest frame into deque (non-blocking, always fresh)
        frame_queue.append(annotated)

        # Handle continuous hold actions every frame (e.g. spacebar for 2x)
        controller.handle_hold(gesture_name)

        # Trigger one-shot actions if gesture held long enough
        action_info = None
        if detector.should_trigger(gesture_name):
            action_info = controller.execute(gesture_name)

        # Update status
        with status_lock:
            current_status["gesture"] = gesture_name
            current_status["fps"] = round(detector.fps, 1)
            current_status["active"] = True
            current_status["finger_count"] = finger_count
            if action_info:
                current_status["action"] = action_info["action"]
                current_status["description"] = action_info["description"]

    cap.release()
    detector.release()
    if controller:
        controller.release_all()   # release spacebar if held
    frame_queue.clear()
    print("[GesturePlay] Detection stopped.")


# ─── MJPEG Stream Generator ───────────────────────────────────────────────────

def generate_frames():
    """
    Yield MJPEG frames from deque.
    Since deque maxlen=1, we always get the freshest frame without waiting.
    """
    while True:
        if not frame_queue:
            time.sleep(0.02)
            continue

        frame = frame_queue[-1]  # always the latest frame

        ret, buffer = cv2.imencode(
            ".jpg", frame,
            [cv2.IMWRITE_JPEG_QUALITY, 75]  # 75 = good quality, fast encode
        )
        if not ret:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n"
        )

        time.sleep(0.025)  # ~40 FPS stream cap


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/api/status")
def api_status():
    with status_lock:
        status = current_status.copy()

    if controller:
        status["recent_actions"] = controller.get_recent_actions(10)
    else:
        status["recent_actions"] = []

    return jsonify(status)


@app.route("/api/toggle", methods=["POST"])
def api_toggle():
    global detection_active, detection_thread, current_status

    if detection_active:
        detection_active = False
        if detection_thread:
            detection_thread.join(timeout=5)
            detection_thread = None

        with status_lock:
            current_status = {
                "gesture": None, "action": None, "description": None,
                "fps": 0, "active": False, "finger_count": 0,
            }

        return jsonify({"status": "stopped", "active": False})
    else:
        detection_active = True
        detection_thread = threading.Thread(target=detection_loop, daemon=True)
        detection_thread.start()
        return jsonify({"status": "started", "active": True})


@app.route("/api/config", methods=["GET"])
def api_get_config():
    return jsonify(load_config())


@app.route("/api/config", methods=["POST"])
def api_update_config():
    data = request.get_json()
    gesture = data.get("gesture")
    action = data.get("action")

    if not gesture or not action:
        return jsonify({"error": "Missing gesture or action"}), 400

    result = update_gesture_action(gesture, action)
    if result is True:
        if controller:
            controller.reload_mappings()
        if detector:
            detector.set_action_labels(controller.gesture_mappings)
        return jsonify({"success": True})
    else:
        return jsonify({"error": result}), 400


@app.route("/api/clear_log", methods=["POST"])
def api_clear_log():
    if controller:
        controller.clear_log()
    return jsonify({"success": True})


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print()
    print("=" * 54)
    print("  GesturePlay -- Gesture-Controlled Media Controller")
    print("=" * 54)
    print("  Open http://localhost:5000 in your browser")
    print("  Press Ctrl+C to quit")
    print("=" * 54)
    print()

    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
