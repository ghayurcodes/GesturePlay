"""
gesture_detector.py - Stabilized detector with neutral-gap gating.
After any trigger, requires hand to be absent 0.6s before next trigger.
This kills ALL transition-state false triggers (the play/pause jumble).
"""
import cv2
import mediapipe as mp
import time
from collections import deque

HOLD_THRESHOLDS = {
    "fist":      0.60,
    "index_up":  0.30,
    "peace":     0.25,
    "three_up":  0.30,
    "open_palm": 0.40,
}

class GestureDetector:
    TIP_IDS = [4, 8, 12, 16, 20]

    def __init__(self, detection_confidence=0.8, tracking_confidence=0.5):
        self.mp_hands = mp.solutions.hands
        self.mp_draw  = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False, max_num_hands=1, model_complexity=0,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )
        self._buffer      = deque(maxlen=8)
        self.STABLE_RATIO = 0.65
        self.current_gesture    = None
        self.gesture_start_time = 0
        self.neutral_gap          = 0.35
        self._waiting_for_neutral = False
        self._neutral_seen_at     = 0.0
        self.last_trigger_time    = 0
        self.cooldown             = 1.5
        self.fps = 0
        self._frame_count = 0
        self._fps_timer   = time.time()
        self.lm_list = []

    def detect(self, frame):
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.hands.process(rgb)
        rgb.flags.writeable = True
        raw_gesture = None
        finger_count = 0
        self.lm_list = []
        if results.multi_hand_landmarks:
            hand = results.multi_hand_landmarks[0]
            self.mp_draw.draw_landmarks(
                frame, hand, self.mp_hands.HAND_CONNECTIONS,
                self.mp_draw.DrawingSpec(color=(180,180,180), thickness=2, circle_radius=3),
                self.mp_draw.DrawingSpec(color=(100,100,100), thickness=2),
            )
            h, w, _ = frame.shape
            self.lm_list = [[i, int(lm.x*w), int(lm.y*h)] for i, lm in enumerate(hand.landmark)]
            finger_count = self._count_fingers()
            raw_gesture  = self._classify(finger_count)
        self._buffer.append(raw_gesture)
        stable = self._stable_gesture()
        if stable:
            self._draw_overlay(frame, stable, finger_count)
        if self._waiting_for_neutral:
            h2 = frame.shape[0]; w2 = frame.shape[1]
            msg = "Lower hand to unlock..."
            (tw,_),_ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.putText(frame, msg, (w2-tw-16, h2-16), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80,140,80), 2, cv2.LINE_AA)
        self._update_fps()
        cv2.putText(frame, f"FPS: {self.fps:.0f}", (16, frame.shape[0]-16), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (70,70,70), 2, cv2.LINE_AA)
        return stable, frame, finger_count

    def should_trigger(self, gesture_name):
        now = time.time()
        if self._waiting_for_neutral:
            if gesture_name is None:
                if self._neutral_seen_at == 0.0:
                    self._neutral_seen_at = now
                elif now - self._neutral_seen_at >= self.neutral_gap:
                    self._waiting_for_neutral = False
                    self._neutral_seen_at = 0.0
                    self.current_gesture = None
                    self.gesture_start_time = 0
            else:
                self._neutral_seen_at = 0.0
            return False
        if gesture_name is None:
            self.current_gesture = None
            self.gesture_start_time = 0
            return False
        if gesture_name != self.current_gesture:
            self.current_gesture = gesture_name
            self.gesture_start_time = now
            return False
        hold_needed = HOLD_THRESHOLDS.get(gesture_name, 0.55)
        if now - self.gesture_start_time < hold_needed:
            return False
        if now - self.last_trigger_time < self.cooldown:
            return False
        self.last_trigger_time = now
        self.gesture_start_time = now
        self._waiting_for_neutral = True
        self._neutral_seen_at = 0.0
        return True

    def release(self):
        self.hands.close()

    def _stable_gesture(self):
        if not self._buffer:
            return None
        counts = {}
        for g in self._buffer:
            counts[g] = counts.get(g, 0) + 1
        best, best_count = None, 0
        for g, c in counts.items():
            if c > best_count:
                best, best_count = g, c
        return best if best_count >= len(self._buffer) * self.STABLE_RATIO else None

    def _count_fingers(self):
        if not self.lm_list:
            return 0
        fingers = []
        # Thumb: Check horizontal distance between tip (4) and base (2)
        # Using a relative threshold based on hand size (distance between 0 and 5)
        hand_size = ((self.lm_list[0][1]-self.lm_list[5][1])**2 + (self.lm_list[0][2]-self.lm_list[5][2])**2)**0.5
        if abs(self.lm_list[4][1] - self.lm_list[2][1]) > hand_size * 0.4:
            fingers.append(1)
        
        # 4 Fingers: Check if tip is above knuckle
        for i in range(1, 5):
            if self.lm_list[self.TIP_IDS[i]][2] < self.lm_list[self.TIP_IDS[i]-2][2]:
                fingers.append(1)
        return sum(fingers)

    def _classify(self, count):
        return {0:"fist", 1:"index_up", 2:"peace", 3:"three_up", 4:"open_palm", 5:"open_palm"}.get(count, None)

    def _draw_overlay(self, frame, gesture, count):
        labels = {
            "fist":      ("FIST  - Play/Pause",  (100,100,100)),
            "index_up":  ("1 FIN - Skip Back",   (140,140,140)),
            "peace":     ("2 FIN - Speed 2x",    (160,160,160)),
            "three_up":  ("3 FIN - Skip Fwd",    (160,160,160)),
            "open_palm": ("PALM  - Mute",         (200,200,200)),
        }
        if gesture in labels:
            text, color = labels[gesture]
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.85, 2)
            cv2.rectangle(frame, (10,10), (22+tw, 46), (25,25,25), -1)
            cv2.putText(frame, text, (16,36), cv2.FONT_HERSHEY_SIMPLEX, 0.85, color, 2, cv2.LINE_AA)
        cv2.putText(frame, f"Fingers: {count}", (16,68), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (110,110,110), 2, cv2.LINE_AA)

    def _update_fps(self):
        self._frame_count += 1
        elapsed = time.time() - self._fps_timer
        if elapsed >= 1.0:
            self.fps = self._frame_count / elapsed
            self._frame_count = 0
            self._fps_timer = time.time()
