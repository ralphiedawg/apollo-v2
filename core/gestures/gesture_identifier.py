import cv2
import mediapipe as mp
import time
import math

mp_hands = mp.solutions.hands
drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands()

cam = cv2.VideoCapture(1)
wake_mode = False
wake_timer = 0
volume = 50  # Simulated volume level
prev_x = None

def is_shaka(hand):
    extended = lambda tip: hand.landmark[tip].y < hand.landmark[tip - 2].y
    curled = lambda tip: hand.landmark[tip].y > hand.landmark[tip - 2].y
    return (
        extended(4) and extended(20) and
        curled(8) and curled(12) and curled(16)
    )

def is_pinching(hand):
    thumb_tip = hand.landmark[4]
    index_tip = hand.landmark[8]
    distance = ((thumb_tip.x - index_tip.x) ** 2 + (thumb_tip.y - index_tip.y) ** 2) ** 0.5
    return distance < 0.06  # tweak threshold as needed

def get_pinch_x(hand):
    thumb_tip = hand.landmark[4]
    index_tip = hand.landmark[8]
    return (thumb_tip.x + index_tip.x) / 2

while True:
    success, img = cam.read()
    if not success:
        continue

    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_img)
    current_time = time.time()

    if results.multi_hand_landmarks:
        for hand in results.multi_hand_landmarks:
            drawing.draw_landmarks(img, hand, mp_hands.HAND_CONNECTIONS)

            if is_shaka(hand):
                print("🤙 Wake gesture detected!")
                wake_mode = True
                wake_timer = current_time + 5
                prev_x = None

            if wake_mode:
                if is_pinching(hand):
                    pinch_x = get_pinch_x(hand)
                    if prev_x is not None:
                        delta = pinch_x - prev_x
                        if abs(delta) > 0.01:
                            volume += int(delta * 100)  # sensitivity scaling
                            volume = max(0, min(100, volume))
                            print(f"🔊 Volume: {volume}")
                    prev_x = pinch_x
                else:
                    prev_x = None  # Reset if no pinch

    if wake_mode and current_time > wake_timer:
        wake_mode = False
        prev_x = None

    cv2.imshow("Apollo Gesture Mode", img)
    if cv2.waitKey(5) & 0xFF == ord("q"):
        break

cam.release()
cv2.destroyAllWindows()
