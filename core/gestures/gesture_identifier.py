import cv2
import mediapipe as mp
import time
import math
import subprocess
import platform

mp_hands = mp.solutions.hands
drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands()

cam = cv2.VideoCapture(0)
volume = 50  # Current volume level (0-100)
is_playing = True  # Track playback state

# State management
active_mode = None  # Can be: None, "shaka_pending", "volume", "action_completed"
shaka_active = False  # Track if shaka is currently being shown
v_sign_detected = False  # Track if V sign has been detected after shaka

# Timers
shaka_timer = 0  # Time to show V sign after shaka
v_sign_timer = 0  # Time to start volume adjustment after V
volume_timer = 0  # Time for volume adjustment mode

# Gesture hold tracking
thumbs_up_start = 0    # Time when thumbs up gesture started
required_hold_time = 1.0  # Seconds required to hold gesture
gesture_cooldown = 0   # Cooldown timer for gesture detection

# Progress tracking
progress_bar_max = 100  # Max width for progress bar

# Check if running on macOS
is_mac = platform.system() == "Darwin"

def control_macos_media(action):
    """
    Control macOS media playback using AppleScript
    
    Actions:
    - "play": Toggle play/pause
    - "next": Skip to next track
    - "prev": Go to previous track
    - "volume_up": Increase volume
    - "volume_down": Decrease volume
    - "volume_set": Set volume to specific level (0-100)
    """
    if not is_mac:
        print(f"[Simulated] Media action: {action}")
        return
        
    if action == "play":
        # Toggle play/pause using AppleScript
        cmd = """
        osascript -e 'tell application "System Events" to keystroke space'
        """
    elif action == "next":
        # Skip to next track using AppleScript
        cmd = """
        osascript -e 'tell application "System Events" to key code 124 using {command down}'
        """
    elif action == "volume_set":
        # Set volume to specific level (0-100)
        # AppleScript expects a value from 0-100
        cmd = f"""
        osascript -e 'set volume output volume {volume}'
        """
    else:
        print(f"Unsupported action: {action}")
        return
        
    try:
        subprocess.run(cmd, shell=True)
        print(f"Media control executed: {action}")
    except Exception as e:
        print(f"Error executing media control: {e}")

def is_shaka(hand):
    extended = lambda tip: hand.landmark[tip].y < hand.landmark[tip - 2].y
    curled = lambda tip: hand.landmark[tip].y > hand.landmark[tip - 2].y
    return (
        extended(4) and extended(20) and
        curled(8) and curled(12) and curled(16)
    )

def is_v_sign(hand):
    # Check if index and middle fingers are extended, others are curled
    extended = lambda tip: hand.landmark[tip].y < hand.landmark[tip - 2].y
    curled = lambda tip: hand.landmark[tip].y > hand.landmark[tip - 2].y
    return (
        extended(8) and   # Index finger extended
        extended(12) and  # Middle finger extended
        curled(16) and    # Ring finger curled
        curled(20)        # Pinky curled
    )

def is_thumbs_up(hand):
    # Check if thumb is extended upward, all other fingers curled
    extended = lambda tip: hand.landmark[tip].y < hand.landmark[tip - 2].y
    curled = lambda tip: hand.landmark[tip].y > hand.landmark[tip - 2].y
    
    # Check thumb is extended and pointing upward
    thumb_extended = hand.landmark[4].y < hand.landmark[3].y < hand.landmark[2].y
    
    # Make sure thumb is pointing generally upward
    thumb_upward = hand.landmark[4].y < hand.landmark[9].y  # Thumb tip is higher than middle finger base
    
    return (
        thumb_extended and thumb_upward and
        curled(8) and   # Index finger curled
        curled(12) and  # Middle finger curled
        curled(16) and  # Ring finger curled
        curled(20)      # Pinky curled
    )

def is_flat_palm(hand):
    # Check if all fingers are extended
    extended = lambda tip: hand.landmark[tip].y < hand.landmark[tip - 2].y
    return (
        extended(4) and   # Thumb extended
        extended(8) and   # Index finger extended
        extended(12) and  # Middle finger extended
        extended(16) and  # Ring finger extended
        extended(20)      # Pinky extended
    )

def get_pinch_distance(hand):
    thumb_tip = hand.landmark[4]
    index_tip = hand.landmark[8]
    distance = ((thumb_tip.x - index_tip.x) ** 2 + (thumb_tip.y - index_tip.y) ** 2) ** 0.5
    return distance

def get_current_system_volume():
    """Get the current system volume level on macOS (0-100)"""
    if not is_mac:
        return 50  # Default value for non-macOS systems
    
    try:
        cmd = "osascript -e 'output volume of (get volume settings)'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            # macOS returns volume as 0-100
            return int(result.stdout.strip())
        else:
            print("Failed to get system volume")
            return 50
    except Exception as e:
        print(f"Error getting system volume: {e}")
        return 50

# Initialize volume with current system volume
if is_mac:
    volume = get_current_system_volume()
    print(f"Current system volume: {volume}")

while True:
    success, img = cam.read()
    if not success:
        continue

    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_img)
    current_time = time.time()
    
    # Check timers for state transitions
    if active_mode == "shaka_pending" and current_time > shaka_timer:
        print("⏰ Time's up! Gesture window expired")
        active_mode = "action_completed"  # Require new shaka
    
    if v_sign_detected and current_time > v_sign_timer:
        print("⏰ Time's up! Volume adjustment window expired")
        v_sign_detected = False
    
    if active_mode == "volume" and current_time > volume_timer:
        print("⏰ Time's up! Volume adjustment mode ended")
        active_mode = "action_completed"  # Require new shaka

    # Reset gesture tracking if no hands detected or not in shaka_pending mode
    if results.multi_hand_landmarks is None or active_mode != "shaka_pending":
        thumbs_up_start = 0

    if results.multi_hand_landmarks:
        for hand in results.multi_hand_landmarks:
            drawing.draw_landmarks(img, hand, mp_hands.HAND_CONNECTIONS)

            # Check for shaka gesture to initiate any mode
            if is_shaka(hand):
                if active_mode is None or active_mode == "action_completed":  # Only if no active mode or previous action completed
                    print("🤙 Shaka gesture detected!")
                    active_mode = "shaka_pending"
                    shaka_timer = current_time + 5.0  # 5 seconds to show gesture
                    print(f"You have 5 seconds to show a gesture")
                    # Reset gesture timers
                    thumbs_up_start = 0
            
            # During shaka pending window
            elif active_mode == "shaka_pending":
                if is_v_sign(hand):
                    print("✌️ V sign detected!")
                    v_sign_detected = True
                    active_mode = None  # Clear shaka pending
                    v_sign_timer = current_time + 5.0  # 5 seconds to start volume adjustment
                    print(f"You have 5 seconds to prepare for volume adjustment")
                    
                    # Get current system volume when entering volume mode
                    if is_mac:
                        volume = get_current_system_volume()
                        print(f"Current system volume: {volume}")
                    
                    # Reset gesture timers
                    thumbs_up_start = 0
                
                elif is_flat_palm(hand) and current_time > gesture_cooldown:
                    # Toggle play/pause with flat palm
                    is_playing = not is_playing
                    status = "▶️ Playing" if is_playing else "⏸️ Paused"
                    print(f"{status}")
                    
                    # Actually control the media playback
                    control_macos_media("play")
                    
                    cv2.putText(img, status, (50, 200), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
                    gesture_cooldown = current_time + 1.0  # 1 second cooldown
                    active_mode = "action_completed"  # One action per shaka
                    # Reset gesture timers
                    thumbs_up_start = 0
                
                elif is_thumbs_up(hand):
                    # Start tracking thumbs up hold time if not already tracking
                    if thumbs_up_start == 0:
                        thumbs_up_start = current_time
                    
                    # Check if held for required time
                    hold_duration = current_time - thumbs_up_start
                    if hold_duration >= required_hold_time and current_time > gesture_cooldown:
                        # Skip to next song
                        print("▶️ Next song")
                        
                        # Actually control the media playback
                        control_macos_media("next")
                        
                        cv2.putText(img, "Next song", (50, 150), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 100, 0), 2)
                        gesture_cooldown = current_time + 1.0  # 1 second cooldown
                        active_mode = "action_completed"  # One action per shaka
                        thumbs_up_start = 0  # Reset timer
                    else:
                        # Show progress bar for hold duration
                        progress = int((hold_duration / required_hold_time) * progress_bar_max)
                        progress = min(progress, progress_bar_max)  # Cap at max
                        
                        # Draw progress bar
                        bar_start = (50, 170)
                        bar_height = 10
                        cv2.rectangle(img, bar_start, (50 + progress_bar_max, 170 + bar_height), (100, 100, 100), -1)
                        cv2.rectangle(img, bar_start, (50 + progress, 170 + bar_height), (0, 255, 0), -1)
                        
                        # Show text
                        cv2.putText(img, "Hold thumbs up for next song...", (50, 150), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                else:
                    # Reset gesture timers if no recognized gesture is detected
                    thumbs_up_start = 0
            
            # If V sign was detected and now we see another gesture, start volume mode
            elif v_sign_detected and not is_v_sign(hand):
                print("🔊 Volume adjustment mode activated")
                active_mode = "volume"
                v_sign_detected = False
                volume_timer = current_time + 5.0  # 5 seconds for volume adjustment
                print(f"Volume mode active for 5 seconds")
            
            # Handle volume adjustment
            elif active_mode == "volume":
                # Get the distance between thumb and index finger
                distance = get_pinch_distance(hand)
                
                # Calculate volume based on distance
                # Min distance ~0.02, max reasonable distance ~0.15
                normalized_distance = min(1.0, max(0.0, (distance - 0.02) / 0.13))
                
                # Map the normalized distance to volume (0-100)
                new_volume = int(normalized_distance * 100)
                
                # Only update if there's a significant change
                if abs(new_volume - volume) > 2:
                    volume = new_volume
                    print(f"🔊 Volume adjusted to: {volume} (distance: {distance:.4f})")
                    
                    # Actually control the system volume
                    control_macos_media("volume_set")
                
                # Draw a line between thumb and index finger with color based on volume
                thumb_tip = hand.landmark[4]
                index_tip = hand.landmark[8]
                
                h, w, c = img.shape
                thumb_x, thumb_y = int(thumb_tip.x * w), int(thumb_tip.y * h)
                index_x, index_y = int(index_tip.x * w), int(index_tip.y * h)
                
                # Color gradient from red (low volume) to green (high volume)
                color = (0, volume * 2.55, 255 - volume * 2.55)  # BGR format
                
                cv2.line(img, (thumb_x, thumb_y), (index_x, index_y), color, 4)
    else:
        # No hands detected, reset gesture timers
        thumbs_up_start = 0

    # Display current state and time remaining
    if active_mode == "shaka_pending":
        time_left = max(0, int(shaka_timer - current_time))
        cv2.putText(img, f"Gesture Window ({time_left}s)", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
        cv2.putText(img, "V: Volume | 👍: Skip | ✋: Play/Pause", (50, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    elif v_sign_detected:
        time_left = max(0, int(v_sign_timer - current_time))
        cv2.putText(img, f"Prepare for Volume ({time_left}s)", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    elif active_mode == "volume":
        time_left = max(0, int(volume_timer - current_time))
        cv2.putText(img, f"Volume Mode ({time_left}s)", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(img, f"VOL: {volume}", (50, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    elif active_mode == "action_completed":
        cv2.putText(img, "Throw another shaka", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    
    # Always show playback status
    status_icon = "▶️" if is_playing else "⏸️"
    cv2.putText(img, f"{status_icon}", (20, 50), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    cv2.imshow("Apollo Gesture Mode", img)
    if cv2.waitKey(5) & 0xFF == ord("q"):
        break

cam.release()
cv2.destroyAllWindows()
