#!/usr/bin/env python3
"""
Apollo v2 - Voice Assistant
Main application file with gesture integration for hands-free control
"""

import os
import subprocess
import time
import datetime
import select
import sys
from typing import Optional, Dict, List, Any

# Try to load dotenv early to ensure environment variables are available
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Environment variables loaded from .env file")
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables may not be loaded.")

# Core Apollo imports
from core.chat import chat_with_apollo
from intents.classifier import get_final_intent
from core.memory.ShortTermMemory import ShortTermMemory
from core.memory.LongTermMemory import LongTermMemory
from core.auth.authentication import Authenticator

# Import gesture framework
gesture_available = False
try:
    from core.gestures.gesture_identifier import ApolloGestureController
    gesture_available = True
except ImportError:
    print("Warning: Gesture framework not available. Gesture control will be disabled.")


def check_module_availability(module_name: str, import_names: List[str]) -> bool:
    """Check if a module is available without causing program exit on failure"""
    try:
        for name in import_names:
            __import__(name)
        return True
    except ImportError:
        print(f"Warning: {module_name} not available. Related features will be disabled.")
        return False


def input_available(timeout=0.1):
    """Check if there's input available on stdin without blocking"""
    return select.select([sys.stdin], [], [], timeout)[0]


def main():
    """Main function for Apollo assistant"""
    # Display startup banner with current date/time
    current_datetime = "2025-07-11 23:33:45"  # Current UTC time
    current_user = "ralphiedawg"  # Current user login
    
    print("\n" + "="*60)
    print(f"Apollo v2 Voice Assistant - Starting Up at {current_datetime} UTC")
    print(f"Current user: {current_user}")
    print("="*60 + "\n")
    
    # Load bypass phrase from environment variable
    bypass_phrase = os.environ.get('AUTH_BYPASS')
    if not bypass_phrase:
        print("Warning: AUTH_BYPASS environment variable not found. Authentication may fail.")
        bypass_phrase = "apollo"  # Default fallback, should be replaced by actual value from .env
    
    # Check for optional modules availability
    tts_available = check_module_availability("Text-to-Speech", ["core.tts.apollo_tts"])
    stt_available = check_module_availability("Speech-to-Text", ["core.stt.WhisperCapture"])
    face_available = check_module_availability("Face Recognition", ["cv2", "face_recognition"])
    
    # Initialize speech components if available
    whisper_capture = None
    apollotts = None
    enable_speech = False
    enable_voice_input = False
    
    # Initialize gesture components if available
    gesture_controller = None
    enable_gestures = False
    
    # Ask for user preferences for available modules
    if tts_available:
        try:
            from core.tts.apollo_tts import ApolloTTS
            enable_speech = input("Enable speech synthesis? (yes/no): ").strip().lower() == "yes"
            if enable_speech:
                print("Initializing text-to-speech...")
                apollotts = ApolloTTS()
        except Exception as e:
            print(f"Error initializing TTS: {e}")
            enable_speech = False
    
    if stt_available:
        try:
            from core.stt.WhisperCapture import WhisperCapture
            enable_voice_input = input("Enable voice input with Whisper? (yes/no): ").strip().lower() == "yes"
            if enable_voice_input:
                print("Initializing speech recognition...")
                try:
                    pause_time = float(input("Seconds to wait during speech pauses (default 2.0): ") or "2.0")
                except ValueError:
                    print("Invalid value, using default 2.0 seconds")
                    pause_time = 2.0
                    
                whisper_capture = WhisperCapture(model_size="base", pause_threshold=pause_time)
                
                # Link components for feedback prevention if both are enabled
                if enable_speech and apollotts:
                    apollotts.set_whisper_capture(whisper_capture)
        except Exception as e:
            print(f"Error initializing STT: {e}")
            enable_voice_input = False
    
    # Determine if wake gesture is required (only when both TTS and STT are enabled)
    require_wake_gesture = enable_speech and enable_voice_input
    
    # Initialize gesture recognition if available (available in all modes now)
    if gesture_available:
        try:
            enable_gestures = input("Enable gesture control with ApolloGestureController? (yes/no): ").strip().lower() == "yes"
            if enable_gestures:
                print("Initializing gesture recognition...")
                camera_index = int(input("Camera index to use (default 0): ") or "0")
                
                # Create a gesture controller in headless mode (no visualization)
                gesture_controller = ApolloGestureController(camera_index=camera_index, headless=True)
                
                # Start processing frames in the background
                if gesture_controller.start_processing():
                    if require_wake_gesture:
                        print("Gesture recognition active. Use 'shaka' gesture (🤙) to wake Apollo.")
                        print("Media controls available through gestures: V-sign for volume, thumbs up for next track, flat palm for play/pause.")
                    else:
                        print("Gesture recognition active for media controls:")
                        print("- Shaka (🤙) + V-sign (✌️): Volume control")
                        print("- Shaka (🤙) + Thumbs up (👍): Next track")
                        print("- Shaka (🤙) + Flat palm (✋): Play/pause")
                else:
                    print("Failed to start gesture recognition. Continuing without gestures.")
                    enable_gestures = False
                    gesture_controller = None
        except Exception as e:
            print(f"Error initializing gesture recognition: {e}")
            enable_gestures = False
            gesture_controller = None
    
    # Handle authentication - CRITICAL FIX: Complete authentication fully before proceeding
    authenticator = Authenticator(
        whisper_capture=None,  # Important: We're not passing whisper_capture here initially
        tts_engine=apollotts if enable_speech else None
    )
    
    # Authentication logic with fix for premature listening
    authenticated_user = current_user
    
    # AUTHENTICATION FLOW: Complete the authentication in stages to prevent premature listening
    print("\n--- Authentication Required ---")
    
    # First handle authentication without voice input to avoid the interruption issue
    authenticated = authenticate_user_text_only(authenticator, bypass_phrase)
    
    # Only after authentication is successful, update with voice components
    if authenticated:
        authenticated_user = authenticator.get_authenticated_user() or current_user
        
        # Now that we've authenticated, we can safely connect the whisper_capture if needed
        if enable_voice_input and whisper_capture:
            # Safe to connect voice input after authentication
            authenticator.set_whisper_capture(whisper_capture)
            
        message = f"Authentication successful! Welcome {authenticated_user}. Starting Apollo..."
        print(message)
        
        if enable_speech and apollotts:
            apollotts.speak(message)
    else:
        message = "Authentication failed. Exiting."
        print(message)
        
        if enable_speech and apollotts:
            apollotts.speak(message)
            
        return  # Exit if authentication failed
    
    # Initialize memory systems
    print("Initializing memory systems...")
    short_term_memory = ShortTermMemory(max_entries=15)
    long_term_memory = LongTermMemory("cache/long_term_memory.json")
    
    # Set up model
    model = "gemma3:4b"
    
    # Main chat loop
    print("\nApollo Interactive Chat (type 'exit' to quit or press Ctrl+C to exit)")
    
    # Gesture control state variables
    running = True
    active_mode = not require_wake_gesture  # Start in active mode unless wake gesture required
    last_interaction_time = time.time()
    inactivity_timeout = 30.0  # Seconds of inactivity before returning to sleep mode
    
    if require_wake_gesture:
        print("Apollo is in sleep mode. Make a 'shaka' gesture (🤙) to wake it up.")
    else:
        print("Apollo is ready. Type your message or use gestures for media control.")
        
    # Set up gesture callbacks
    if enable_gestures and gesture_controller:
        def on_shaka_detected():
            """Called when a shaka gesture is detected"""
            nonlocal active_mode, last_interaction_time
            if require_wake_gesture and not active_mode:
                print("\nShaka gesture detected! Waking up Apollo...")
                active_mode = True
                last_interaction_time = time.time()
                
                if enable_speech and apollotts:
                    apollotts.speak("Hello! I'm listening.")
        
        def on_gesture_window_expired():
            """Called when the gesture window expires"""
            # Nothing to do here for now
            pass
            
        def on_play_pause():
            """Called when play/pause is toggled"""
            print("\n[Gesture] Play/Pause toggled")
            
        def on_next_track():
            """Called when next track is requested"""
            print("\n[Gesture] Next track")
            
        def on_volume_change(volume):
            """Called when volume is changed"""
            print(f"\n[Gesture] Volume set to {volume}")
            
        # Register callbacks
        gesture_controller.on_shaka_detected = on_shaka_detected
        gesture_controller.on_gesture_window_expired = on_gesture_window_expired
        gesture_controller.on_play_pause = on_play_pause
        gesture_controller.on_next_track = on_next_track
        gesture_controller.on_volume_change = on_volume_change
    
    def speak(message: str):
        """Helper function to handle text-to-speech with proper listening control"""
        if not (enable_speech and apollotts):
            return
            
        # ApolloTTS class already handles speaking state coordination with WhisperCapture
        apollotts.speak(message)
    
    def check_for_timeout():
        """Check if we should enter sleep mode due to inactivity"""
        if not require_wake_gesture:
            return False  # Only enter sleep mode if wake gesture is required
            
        current_time = time.time()
        time_since_interaction = current_time - last_interaction_time
        
        if time_since_interaction > inactivity_timeout:
            print(f"\nNo activity detected for {inactivity_timeout} seconds. Entering sleep mode.")
            if enable_speech and apollotts:
                apollotts.speak("Going to sleep mode. Make a shaka gesture to wake me up.")
            return True
            
        return False
    
    def get_user_input() -> Optional[str]:
        """Get input from the user, with proper handling of voice/text/gesture modes"""
        nonlocal active_mode, last_interaction_time
        
        # In active mode with voice input enabled
        if active_mode and enable_voice_input and whisper_capture:
            print("\nSay something (or type 'manual' to switch to keyboard input for this turn):")
            try:
                # Ensure listening is active before starting
                whisper_capture.resume_listening()
                user_input = whisper_capture.listen_and_transcribe()
                
                if not user_input:
                    print("No speech detected. Please try again or type your message.")
                    return ""
                
                if user_input.strip().lower() == "manual":
                    last_interaction_time = time.time()
                    return input("\nYou (typing): ")
                
                print(f"You (voice): {user_input}")
                last_interaction_time = time.time()  # Update last interaction time
                return user_input
                
            except KeyboardInterrupt:
                print("\nSwitching to manual input for this turn.")
                last_interaction_time = time.time()
                return input("\nYou (typing): ")
                
        # In active mode with only text input
        elif active_mode:
            last_interaction_time = time.time()
            return input("\nYou: ")
            
        # In sleep mode - process gesture inputs and check for keyboard input
        else:
            # Check for keyboard input (which wakes up from sleep mode)
            if input_available(0.1):
                active_mode = True
                last_interaction_time = time.time()
                return input("\nYou (typing): ")
            
            # Process gestures when in sleep mode
            if enable_gestures and gesture_controller:
                # Process the next camera frame (to detect wake gesture)
                gesture_controller.process_next_frame()
            
            # Sleep mode, no input yet
            sys.stdout.write("\rApollo is sleeping. Waiting for wake gesture (🤙)..." + " " * 10)
            sys.stdout.flush()
            time.sleep(0.1)  # Prevent CPU hogging
            return None
    
    def format_memory_context(memory_entries: List[Dict[str, Any]]) -> str:
        """Format memory entries into a context string"""
        if not memory_entries:
            return ""
        
        context = "Conversation history:\n"
        for entry in memory_entries:
            context += f"[{entry['timestamp']}] User: {entry['user']}\nApollo: {entry['response']}\n"
        context += "\n"
        return context
    
    try:
        # Main interaction loop
        while running:
            # Process gesture input in both active and sleep modes
            # This ensures media controls work regardless of wake/sleep state
            if enable_gestures and gesture_controller:
                gesture_controller.process_next_frame()
            
            # Check for timeout and enter sleep mode if necessary
            # (only applies when wake gesture is required)
            if active_mode and check_for_timeout():
                active_mode = False
                continue
                
            # Get user input based on current mode
            user_input = get_user_input()
            
            # Skip cycle if in sleep mode with no input or empty input
            if not active_mode or not user_input:
                continue
                
            # Handle empty input
            if user_input.strip() == "":
                print("Sorry, I didn't catch that. Could you please try again?")
                continue
                
            # Handle exit command
            if user_input.strip().lower() in ("exit", "quit"):
                print("Exiting chat. Goodbye!")
                speak("Goodbye!")
                running = False
                break
            
            # Determine intent
            intent_result = get_final_intent(user_input)
            intent = intent_result.get("intent", "none")
            
            # Get memory context
            memory_context = format_memory_context(short_term_memory.get_context())
            
            # Process by intent type
            if intent in ("none", "general_query"):
                # General conversation
                prompt = memory_context + "User: " + user_input
                response = chat_with_apollo(model, prompt, False)
                print(f"Apollo: {response}")
                speak(response)
                short_term_memory.remember(user_input, response)
                
            elif intent == "store_info":
                # Store information to long-term memory
                fact = user_input
                new_fact = long_term_memory.remember(fact, user_input)
                response = f"I've stored your information as a fact: \"{new_fact['fact']}\""
                print(f"Apollo: {response}")
                speak(response)
                short_term_memory.remember(user_input, response)
                
            elif intent == "retrieve_info":
                # Retrieve information from long-term memory
                all_facts = long_term_memory.recall_all()
                prompt = (f"{memory_context} This user's prompt seems to be pertaining to stored information. "
                         f"Answer the user's question based off of your stored info: {all_facts}. "
                         f"The user's input is: {user_input}")
                response = chat_with_apollo(model, prompt, False)
                print(f"Apollo: {response}")
                speak(response)
                short_term_memory.remember(user_input, response)
                
            else:
                # Execute intent through apolloctl
                try:
                    out = subprocess.run(
                        ["./go/apolloctl", intent],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=True
                    )
                    print(f"[Apollo executed intent: {intent}]")
                    prompt = (
                        memory_context +
                        f" The user has asked the question {user_input}. "
                        f"Summarize the result of the command {intent} and return it to me. "
                        f"The output is: {out.stdout}"
                    )
                    result = chat_with_apollo(model, prompt, False)
                    print(f"Apollo: {result}")
                    speak(result)
                    short_term_memory.remember(user_input, result)
                except subprocess.CalledProcessError as e:
                    error_msg = f"Error executing intent '{intent}': {e.stderr}"
                    print(f"Apollo: {error_msg}")
                    speak(error_msg)
                    short_term_memory.remember(user_input, error_msg)
                
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Shutting down Apollo.")
    finally:
        # Clean up resources
        print("\nShutting down Apollo...")
        
        if enable_voice_input and whisper_capture:
            # Any cleanup needed for whisper_capture
            pass
            
        if enable_speech and apollotts:
            # Any cleanup needed for apollotts
            pass
            
        if enable_gestures and gesture_controller:
            # Stop the gesture controller
            gesture_controller.stop()
            print("Gesture controller stopped.")


# Helper function for text-only authentication
def authenticate_user_text_only(authenticator, bypass_phrase):
    """Text-only authentication to avoid the voice input issues"""
    # Implementation to authenticate using the bypass phrase from .env
    print("Enter bypass phrase for authentication:")
    user_input = input("> ")
    
    # Verify against the bypass phrase loaded from .env
    if user_input == bypass_phrase:
        # Set authentication state in the authenticator
        authenticator._authenticated = True
        authenticator._authenticated_user = "ralphiedawg"  # Current user login
        return True
    return False


# Add a method to set whisper_capture after authentication
def set_whisper_capture(self, whisper_capture):
    """Set whisper_capture after authentication is complete"""
    self._whisper_capture = whisper_capture
    

# Patch the Authenticator class
def patch_authenticator():
    """Apply patches to the Authenticator class"""
    # Add the set_whisper_capture method to Authenticator
    Authenticator.set_whisper_capture = set_whisper_capture


if __name__ == "__main__":
    # Apply the patch to the Authenticator class
    patch_authenticator()
    
    # Run the main function
    main()
