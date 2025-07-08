import cv2
import mediapipe as mp
import time
import math

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

def get_pinch_distance(hand):
    """Calculate the distance between thumb tip and index tip"""
    thumb_tip = hand.landmark[4]
    index_tip = hand.landmark[8]
    distance = ((thumb_tip.x - index_tip.x) ** 2 + (thumb_tip.y - index_tip.y) ** 2) ** 0.5
    return distance

def distance_to_volume(distance):
    """Map pinch distance to volume level (0-100)
    Closer distance = lower volume, further distance = higher volume
    """
    # Define distance thresholds
    min_distance = 0.02  # Very close pinch = volume 0
    max_distance = 0.15  # Wide pinch = volume 100
    
    # Clamp distance to our range
    distance = max(min_distance, min(max_distance, distance))
    
    # Map distance to volume linearly
    volume = int(((distance - min_distance) / (max_distance - min_distance)) * 100)
    return max(0, min(100, volume))

def main():
    """Main gesture detection loop"""
    mp_hands = mp.solutions.hands
    drawing = mp.solutions.drawing_utils
    hands = mp_hands.Hands()

    cam = cv2.VideoCapture(1)
    wake_mode = False
    wake_timer = 0
    volume = 50  # Simulated volume level

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

                if wake_mode:
                    if is_pinching(hand):
                        # Use distance-based volume control
                        pinch_distance = get_pinch_distance(hand)
                        volume = distance_to_volume(pinch_distance)
                        print(f"🔊 Volume: {volume} (distance: {pinch_distance:.3f})")
                    else:
                        # When not pinching, show current volume
                        pass

        if wake_mode and current_time > wake_timer:
            wake_mode = False

        cv2.imshow("Apollo Gesture Mode", img)
        if cv2.waitKey(5) & 0xFF == ord("q"):
            break

    cam.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
