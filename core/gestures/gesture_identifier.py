import cv2
import mediapipe as mp
import time
import math
import subprocess
import platform
from typing import Callable, Dict, Optional, Tuple

class ApolloGestureController:
    """
    A class to detect and interpret hand gestures for controlling media playback on macOS.
    
    This controller can detect:
    - Shaka gesture: To initiate gesture mode
    - V sign: To enter volume adjustment mode
    - Thumbs up (held for 1 second): To skip to next song
    - Flat palm: To toggle play/pause
    
    Usage:
        controller = ApolloGestureController(camera_index=0)
        controller.start()
        # To stop:
        controller.stop()
        
        # To use as event-driven:
        controller = ApolloGestureController(camera_index=0, headless=True)
        controller.on_play_pause = lambda: print("Play/Pause toggled")
        controller.on_next_track = lambda: print("Next track")
        controller.on_volume_change = lambda vol: print(f"Volume set to {vol}")
        controller.start_processing()
        # Call controller.stop() when done
    """
    
    def __init__(self, camera_index: int = 0, headless: bool = False, 
                 gesture_window_time: float = 5.0, hold_time: float = 1.0):
        """
        Initialize the gesture controller.
        
        Args:
            camera_index: Index of the camera to use
            headless: If True, don't show the camera feed
            gesture_window_time: Time window for gestures after shaka (seconds)
            hold_time: Time required to hold thumbs up for next track (seconds)
        """
        # MediaPipe setup
        self.mp_hands = mp.solutions.hands
        self.drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands()
        
        # Camera setup
        self.camera_index = camera_index
        self.cam = None
        self.headless = headless
        
        # System info
        self.is_mac = platform.system() == "Darwin"
        
        # State management
        self.active_mode = None  # Can be: None, "shaka_pending", "volume", "action_completed"
        self.v_sign_detected = False
        self.is_playing = True
        self.volume = 50  # Current volume level (0-100)
        
        # Timers
        self.shaka_timer = 0
        self.v_sign_timer = 0
        self.volume_timer = 0
        self.thumbs_up_start = 0
        self.required_hold_time = hold_time
        self.gesture_cooldown = 0
        self.gesture_window_time = gesture_window_time
        
        # Progress tracking
        self.progress_bar_max = 100
        
        # Event callbacks
        self.on_play_pause = None
        self.on_next_track = None
        self.on_volume_change = None
        self.on_shaka_detected = None
        self.on_gesture_window_expired = None
        
        # Running state
        self.running = False
    
    def _initialize_camera(self):
        """Initialize the camera capture."""
        if self.cam is None:
            self.cam = cv2.VideoCapture(self.camera_index)
        return self.cam.isOpened()
    
    def get_current_system_volume(self) -> int:
        """Get the current system volume level on macOS (0-100)"""
        if not self.is_mac:
            return self.volume  # Return current stored volume for non-macOS systems
        
        try:
            cmd = "osascript -e 'output volume of (get volume settings)'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                # macOS returns volume as 0-100
                return int(result.stdout.strip())
            else:
                print("Failed to get system volume")
                return self.volume
        except Exception as e:
            print(f"Error getting system volume: {e}")
            return self.volume
    
    def control_macos_media(self, action: str) -> bool:
        """
        Control macOS media playback using AppleScript
        
        Args:
            action: One of "play", "next", "volume_set"
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_mac:
            print(f"[Simulated] Media action: {action}")
            return True
            
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
            cmd = f"""
            osascript -e 'set volume output volume {self.volume}'
            """
        else:
            print(f"Unsupported action: {action}")
            return False
            
        try:
            subprocess.run(cmd, shell=True)
            print(f"Media control executed: {action}")
            return True
        except Exception as e:
            print(f"Error executing media control: {e}")
            return False
    
    def _is_shaka(self, hand) -> bool:
        """Check if hand is forming a shaka gesture."""
        extended = lambda tip: hand.landmark[tip].y < hand.landmark[tip - 2].y
        curled = lambda tip: hand.landmark[tip].y > hand.landmark[tip - 2].y
        return (
            extended(4) and extended(20) and
            curled(8) and curled(12) and curled(16)
        )

    def _is_v_sign(self, hand) -> bool:
        """Check if hand is forming a V sign."""
        extended = lambda tip: hand.landmark[tip].y < hand.landmark[tip - 2].y
        curled = lambda tip: hand.landmark[tip].y > hand.landmark[tip - 2].y
        return (
            extended(8) and   # Index finger extended
            extended(12) and  # Middle finger extended
            curled(16) and    # Ring finger curled
            curled(20)        # Pinky curled
        )

    def _is_thumbs_up(self, hand) -> bool:
        """Check if hand is forming a thumbs up gesture."""
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

    def _is_flat_palm(self, hand) -> bool:
        """Check if hand is forming a flat palm gesture."""
        extended = lambda tip: hand.landmark[tip].y < hand.landmark[tip - 2].y
        return (
            extended(4) and   # Thumb extended
            extended(8) and   # Index finger extended
            extended(12) and  # Middle finger extended
            extended(16) and  # Ring finger extended
            extended(20)      # Pinky extended
        )

    def _get_pinch_distance(self, hand) -> float:
        """Get the distance between thumb and index finger."""
        thumb_tip = hand.landmark[4]
        index_tip = hand.landmark[8]
        distance = ((thumb_tip.x - index_tip.x) ** 2 + (thumb_tip.y - index_tip.y) ** 2) ** 0.5
        return distance
    
    def toggle_play_pause(self):
        """Toggle media play/pause state."""
        self.is_playing = not self.is_playing
        self.control_macos_media("play")
        if callable(self.on_play_pause):
            self.on_play_pause()
    
    def next_track(self):
        """Skip to the next track."""
        self.control_macos_media("next")
        if callable(self.on_next_track):
            self.on_next_track()
    
    def set_volume(self, volume_level: int):
        """Set the system volume level."""
        self.volume = max(0, min(100, volume_level))
        self.control_macos_media("volume_set")
        if callable(self.on_volume_change):
            self.on_volume_change(self.volume)
    
    def _process_frame(self, img):
        """Process a single frame to detect and interpret gestures."""
        current_time = time.time()
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_img)
        
        # Check timers for state transitions
        if self.active_mode == "shaka_pending" and current_time > self.shaka_timer:
            print("⏰ Time's up! Gesture window expired")
            self.active_mode = "action_completed"  # Require new shaka
            if callable(self.on_gesture_window_expired):
                self.on_gesture_window_expired()
        
        if self.v_sign_detected and current_time > self.v_sign_timer:
            print("⏰ Time's up! Volume adjustment window expired")
            self.v_sign_detected = False
        
        if self.active_mode == "volume" and current_time > self.volume_timer:
            print("⏰ Time's up! Volume adjustment mode ended")
            self.active_mode = "action_completed"  # Require new shaka

        # Reset gesture tracking if no hands detected or not in shaka_pending mode
        if results.multi_hand_landmarks is None or self.active_mode != "shaka_pending":
            self.thumbs_up_start = 0

        if results.multi_hand_landmarks:
            for hand in results.multi_hand_landmarks:
                if not self.headless:
                    self.drawing.draw_landmarks(img, hand, self.mp_hands.HAND_CONNECTIONS)

                # Check for shaka gesture to initiate any mode
                if self._is_shaka(hand):
                    if self.active_mode is None or self.active_mode == "action_completed":
                        print("🤙 Shaka gesture detected!")
                        self.active_mode = "shaka_pending"
                        self.shaka_timer = current_time + self.gesture_window_time
                        print(f"You have {self.gesture_window_time} seconds to show a gesture")
                        # Reset gesture timers
                        self.thumbs_up_start = 0
                        if callable(self.on_shaka_detected):
                            self.on_shaka_detected()
                
                # During shaka pending window
                elif self.active_mode == "shaka_pending":
                    if self._is_v_sign(hand):
                        print("✌️ V sign detected!")
                        self.v_sign_detected = True
                        self.active_mode = None  # Clear shaka pending
                        self.v_sign_timer = current_time + self.gesture_window_time
                        print(f"You have {self.gesture_window_time} seconds to prepare for volume adjustment")
                        
                        # Get current system volume when entering volume mode
                        if self.is_mac:
                            self.volume = self.get_current_system_volume()
                            print(f"Current system volume: {self.volume}")
                        
                        # Reset gesture timers
                        self.thumbs_up_start = 0
                    
                    elif self._is_flat_palm(hand) and current_time > self.gesture_cooldown:
                        # Toggle play/pause with flat palm
                        status = "Playing" if not self.is_playing else "Paused"
                        print(f"{'▶️' if not self.is_playing else '⏸️'} {status}")
                        
                        # Actually control the media playback
                        self.toggle_play_pause()
                        
                        if not self.headless:
                            cv2.putText(img, status, (50, 200), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
                        self.gesture_cooldown = current_time + 1.0  # 1 second cooldown
                        self.active_mode = "action_completed"  # One action per shaka
                        # Reset gesture timers
                        self.thumbs_up_start = 0
                    
                    elif self._is_thumbs_up(hand):
                        # Start tracking thumbs up hold time if not already tracking
                        if self.thumbs_up_start == 0:
                            self.thumbs_up_start = current_time
                        
                        # Check if held for required time
                        hold_duration = current_time - self.thumbs_up_start
                        if hold_duration >= self.required_hold_time and current_time > self.gesture_cooldown:
                            # Skip to next song
                            print("▶️ Next song")
                            
                            # Actually control the media playback
                            self.next_track()
                            
                            if not self.headless:
                                cv2.putText(img, "Next song", (50, 150), 
                                          cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 100, 0), 2)
                            self.gesture_cooldown = current_time + 1.0  # 1 second cooldown
                            self.active_mode = "action_completed"  # One action per shaka
                            self.thumbs_up_start = 0  # Reset timer
                        elif not self.headless:
                            # Show progress bar for hold duration
                            progress = int((hold_duration / self.required_hold_time) * self.progress_bar_max)
                            progress = min(progress, self.progress_bar_max)  # Cap at max
                            
                            # Draw progress bar
                            bar_start = (50, 170)
                            bar_height = 10
                            cv2.rectangle(img, bar_start, (50 + self.progress_bar_max, 170 + bar_height), (100, 100, 100), -1)
                            cv2.rectangle(img, bar_start, (50 + progress, 170 + bar_height), (0, 255, 0), -1)
                            
                            # Show text
                            cv2.putText(img, "Hold thumbs up for next song...", (50, 150), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                    else:
                        # Reset gesture timers if no recognized gesture is detected
                        self.thumbs_up_start = 0
                
                # If V sign was detected and now we see another gesture, start volume mode
                elif self.v_sign_detected and not self._is_v_sign(hand):
                    print("🔊 Volume adjustment mode activated")
                    self.active_mode = "volume"
                    self.v_sign_detected = False
                    self.volume_timer = current_time + self.gesture_window_time
                    print(f"Volume mode active for {self.gesture_window_time} seconds")
                
                # Handle volume adjustment
                elif self.active_mode == "volume":
                    # Get the distance between thumb and index finger
                    distance = self._get_pinch_distance(hand)
                    
                    # Calculate volume based on distance
                    # Min distance ~0.02, max reasonable distance ~0.15
                    normalized_distance = min(1.0, max(0.0, (distance - 0.02) / 0.13))
                    
                    # Map the normalized distance to volume (0-100)
                    new_volume = int(normalized_distance * 100)
                    
                    # Only update if there's a significant change
                    if abs(new_volume - self.volume) > 2:
                        print(f"🔊 Volume adjusted to: {new_volume} (distance: {distance:.4f})")
                        
                        # Actually control the system volume
                        self.set_volume(new_volume)
                    
                    if not self.headless:
                        # Draw a line between thumb and index finger with color based on volume
                        thumb_tip = hand.landmark[4]
                        index_tip = hand.landmark[8]
                        
                        h, w, c = img.shape
                        thumb_x, thumb_y = int(thumb_tip.x * w), int(thumb_tip.y * h)
                        index_x, index_y = int(index_tip.x * w), int(index_tip.y * h)
                        
                        # Color gradient from red (low volume) to green (high volume)
                        color = (0, self.volume * 2.55, 255 - self.volume * 2.55)  # BGR format
                        
                        cv2.line(img, (thumb_x, thumb_y), (index_x, index_y), color, 4)
        else:
            # No hands detected, reset gesture timers
            self.thumbs_up_start = 0

        # Add on-screen display if not in headless mode
        if not self.headless:
            # Display current state and time remaining
            if self.active_mode == "shaka_pending":
                time_left = max(0, int(self.shaka_timer - current_time))
                cv2.putText(img, f"Gesture Window ({time_left}s)", (50, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
                cv2.putText(img, "V: Volume | 👍: Skip | ✋: Play/Pause", (50, 100), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            elif self.v_sign_detected:
                time_left = max(0, int(self.v_sign_timer - current_time))
                cv2.putText(img, f"Prepare for Volume ({time_left}s)", (50, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            elif self.active_mode == "volume":
                time_left = max(0, int(self.volume_timer - current_time))
                cv2.putText(img, f"Volume Mode ({time_left}s)", (50, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(img, f"VOL: {self.volume}", (50, 100), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            elif self.active_mode == "action_completed":
                cv2.putText(img, "Throw another shaka", (50, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            
            # Always show playback status
            status_icon = "▶️" if self.is_playing else "⏸️"
            cv2.putText(img, f"{status_icon}", (20, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Display the image
            cv2.imshow("Apollo Gesture Mode", img)
        
        return img
    
    def start(self):
        """Start the gesture controller with visualization."""
        if not self._initialize_camera():
            print("Failed to initialize camera")
            return False
        
        self.running = True
        
        while self.running:
            success, img = self.cam.read()
            if not success:
                continue
            
            self._process_frame(img)
            
            if not self.headless and cv2.waitKey(5) & 0xFF == ord("q"):
                break
        
        self.stop()
        return True
    
    def start_processing(self):
        """Start processing frames without visualization (for integration)."""
        if not self._initialize_camera():
            print("Failed to initialize camera")
            return False
        
        self.headless = True
        self.running = True
        
        # Get current system volume
        if self.is_mac:
            self.volume = self.get_current_system_volume()
        
        return True
    
    def process_next_frame(self):
        """Process the next frame from the camera (for integration)."""
        if not self.running:
            return None
        
        success, img = self.cam.read()
        if not success:
            return None
        
        return self._process_frame(img)
    
    def stop(self):
        """Stop the gesture controller."""
        self.running = False
        if self.cam is not None:
            self.cam.release()
            self.cam = None
        
        if not self.headless:
            cv2.destroyAllWindows()


# Make the script runnable directly, just like the original version
if __name__ == "__main__":
    # Create a controller with default settings (camera 0, not headless)
    controller = ApolloGestureController(camera_index=1)
    
    # This will start the controller with full visualization, 
    # just like the original script
    print("Starting Apollo Gesture Controller")
    print("Press 'q' to exit")
    controller.start()
