# =========================================================
# Hand Gesture Media Controller
# =========================================================
# Controls:
#
# ✊ Fist          -> Pause
# ✋ Open Palm     -> Play
# ☝ One Finger    -> 1x Speed
# ✌ Victory Sign  -> 2x Speed
#
# Press:
#   q -> Quit
#   c -> Change key bindings
# =========================================================

import cv2
import mediapipe as mp
import pyautogui
import time

# =========================================================
# MediaPipe Setup
# =========================================================

mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

tipIds = [4, 8, 12, 16, 20]

# =========================================================
# Camera Setup
# =========================================================

wCam, hCam = 720, 640

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Cannot access webcam")
    exit()

cap.set(3, wCam)
cap.set(4, hCam)

# =========================================================
# Action Delay
# =========================================================

last_action = time.time()
action_delay = 1.2

# =========================================================
# Default Controls
# =========================================================

controls = {
    "PLAY": "space",
    "PAUSE": "space",
    "1X": "1",
    "2X": "2"
}

# =========================================================
# Change Controls Function
# =========================================================

def change_controls():

    global controls

    print("\n======= CHANGE CONTROLS =======")

    play_key = input("Key for PLAY gesture: ")
    pause_key = input("Key for PAUSE gesture: ")
    speed1_key = input("Key for 1X gesture: ")
    speed2_key = input("Key for 2X gesture: ")

    if play_key != "":
        controls["PLAY"] = play_key

    if pause_key != "":
        controls["PAUSE"] = pause_key

    if speed1_key != "":
        controls["1X"] = speed1_key

    if speed2_key != "":
        controls["2X"] = speed2_key

    print("\nUpdated Controls:")
    print(controls)
    print("================================\n")

# =========================================================
# Finger Detection Function
# =========================================================

def fingerPosition(image, results, handNo=0):

    lmList = []

    if results.multi_hand_landmarks:

        myHand = results.multi_hand_landmarks[handNo]

        for id, lm in enumerate(myHand.landmark):

            h, w, c = image.shape

            cx, cy = int(lm.x * w), int(lm.y * h)

            lmList.append([id, cx, cy])

    return lmList

# =========================================================
# Count Fingers Function
# =========================================================

def countFingers(lmList):

    fingers = []

    # Thumb
    if lmList[4][1] > lmList[3][1]:
        fingers.append(1)
    else:
        fingers.append(0)

    # Other fingers
    for id in range(1, 5):

        if lmList[tipIds[id]][2] < lmList[tipIds[id] - 2][2]:
            fingers.append(1)

        else:
            fingers.append(0)

    return fingers.count(1)

# =========================================================
# Main Program
# =========================================================

print("========================================")
print("Hand Gesture Media Controller Started")
print("Press 'q' to Quit")
print("Press 'c' to Change Controls")
print("========================================")

with mp_hands.Hands(
    min_detection_confidence=0.8,
    min_tracking_confidence=0.5,
    max_num_hands=1
) as hands:

    while cap.isOpened():

        success, image = cap.read()

        if not success:
            continue

        # Flip image
        image = cv2.flip(image, 1)

        # Convert to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        rgb_image.flags.writeable = False

        # Process hands
        results = hands.process(rgb_image)

        rgb_image.flags.writeable = True

        # =================================================
        # Draw Landmarks
        # =================================================

        if results.multi_hand_landmarks:

            for hand_landmarks in results.multi_hand_landmarks:

                mp_drawing.draw_landmarks(
                    image,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS
                )

        # =================================================
        # Finger Detection
        # =================================================

        lmList = fingerPosition(image, results)

        if len(lmList) != 0:

            totalFingers = countFingers(lmList)

            current_time = time.time()

            # Display finger count
            cv2.putText(
                image,
                f'Fingers: {totalFingers}',
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

            # =============================================
            # ✊ FIST = PAUSE
            # =============================================

            if totalFingers == 0:

                cv2.putText(
                    image,
                    "PAUSE",
                    (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2
                )

                if current_time - last_action > action_delay:

                    pyautogui.press(controls["PAUSE"])

                    print("PAUSE")

                    last_action = current_time

            # =============================================
            # ✋ OPEN HAND = PLAY
            # =============================================

            elif totalFingers == 5:

                cv2.putText(
                    image,
                    "PLAY",
                    (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2
                )

                if current_time - last_action > action_delay:

                    pyautogui.press(controls["PLAY"])

                    print("PLAY")

                    last_action = current_time

            # =============================================
            # ☝ ONE FINGER = 1X SPEED
            # =============================================

            elif totalFingers == 1:

                cv2.putText(
                    image,
                    "1X SPEED",
                    (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (255, 255, 0),
                    2
                )

                if current_time - last_action > action_delay:

                    pyautogui.press(controls["1X"])

                    print("1X SPEED")

                    last_action = current_time

            # =============================================
            # ✌ TWO FINGERS = 2X SPEED
            # =============================================

            elif totalFingers == 2:

                cv2.putText(
                    image,
                    "2X SPEED",
                    (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (255, 0, 255),
                    2
                )

                if current_time - last_action > action_delay:

                    pyautogui.press(controls["2X"])

                    print("2X SPEED")

                    last_action = current_time

        # =================================================
        # Show Current Controls on Screen
        # =================================================

        cv2.putText(
            image,
            f"Play:{controls['PLAY']}  Pause:{controls['PAUSE']}",
            (20, 580),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        cv2.putText(
            image,
            f"1X:{controls['1X']}  2X:{controls['2X']}",
            (20, 610),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        # =================================================
        # Show Window
        # =================================================

        cv2.imshow("Gesture Media Controller", image)

        # =================================================
        # Keyboard Controls
        # =================================================

        key = cv2.waitKey(1) & 0xFF

        # Quit
        if key == ord('q'):
            break

        # Change Controls
        elif key == ord('c'):
            change_controls()

# =========================================================
# Cleanup
# =========================================================

cap.release()
cv2.destroyAllWindows()

print("Program Closed")