"""
Authentication module for Apollo Assistant
Handles user authentication using facial recognition and bypass phrase
"""

import os
import time
import re
import logging
from datetime import datetime

# Set up logging for authentication
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("apollo.auth")

class Authenticator:
    def __init__(self, whisper_capture=None, tts_engine=None):
        """
        Initialize the authenticator
        
        Args:
            whisper_capture: Speech recognition module (optional)
            tts_engine: Text-to-speech module (optional)
        """
        self.whisper_capture = whisper_capture
        self.tts_engine = tts_engine
        self.authenticated_user = None
        
        # Create auth directory if it doesn't exist
        self.auth_dir = "auth"
        if not os.path.exists(self.auth_dir):
            os.makedirs(self.auth_dir)
            logger.info(f"Created {self.auth_dir} directory for authentication files")
        
        # Create logs directory if it doesn't exist
        self.log_dir = "logs"
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            logger.info(f"Created {self.log_dir} directory for log files")
        
        self.auth_log_file = os.path.join(self.log_dir, "auth_log.txt")
        
        # Authentication settings
        self.face_timeout = 15  # seconds for facial recognition timeout
        
        # Load bypass phrase from environment
        self.bypass_phrase = os.getenv("AUTH_BYPASS", "default_bypass_phrase")
    
    def _speak(self, message):
        """Speak a message if TTS is available"""
        print(message)
        if self.tts_engine:
            # Pause listening while speaking to prevent feedback
            if self.whisper_capture:
                self.whisper_capture.pause_listening()
            self.tts_engine.speak(message)
            # Resume after speaking
            if self.whisper_capture:
                time.sleep(0.3)  # Small delay to ensure audio is finished
                self.whisper_capture.resume_listening()
    
    def get_user_input(self, prompt_text, speak_prompt=True):
        """Get user input via speech or text"""
        if speak_prompt and self.tts_engine:
            self._speak(prompt_text)
        elif speak_prompt:
            print(prompt_text)
        
        if self.whisper_capture:
            if not speak_prompt:
                print(prompt_text)
                
            print("Listening... (Say 'manual' to switch to typing)")
            try:
                user_input = self.whisper_capture.listen_and_transcribe()
                if user_input is None or user_input.strip().lower() == "manual":
                    user_input = input(f"{prompt_text}: ")
                else:
                    print(f"You said: {user_input}")
                return user_input
            except KeyboardInterrupt:
                print("\nSwitching to manual input.")
                user_input = input(f"{prompt_text}: ")
                return user_input
        else:
            user_input = input(f"{prompt_text}: ")
            return user_input
    
    def log_authentication_attempt(self, username, success):
        """Log authentication attempts to a file"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        status = "SUCCESS" if success else "FAILED"
        
        try:
            with open(self.auth_log_file, "a") as f:
                f.write(f"{timestamp} | {username} | {status}\n")
            
            logger.info(f"Authentication attempt: {username} - {status}")
        except Exception as e:
            logger.error(f"Error logging authentication: {e}")
    
    def clean_text_for_comparison(self, text):
        """
        Clean text for comparison by:
        1. Converting to lowercase
        2. Removing punctuation
        3. Standardizing whitespace
        4. Handling common speech recognition issues
        """
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove all punctuation
        text = re.sub(r'[^\w\s]', '', text)
        
        # Standardize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Handle common speech-to-text substitutions
        common_substitutions = {
            "to": "2", "too": "2", "two": "2",
            "for": "4", "four": "4",
            "ate": "8", "wait": "8"
        }
        
        words = text.split()
        for i, word in enumerate(words):
            if word in common_substitutions:
                words[i] = common_substitutions[word]
        
        return " ".join(words)
    
    def handle_bypass(self):
        """Handle authentication using bypass phrase"""
        self._speak("User not authorized. Please input the bypass phrase.")
        
        # Skip authentication if bypass is set to "NONE" (for development)
        if self.bypass_phrase == "NONE":
            self._speak("Bypass authentication enabled. Proceeding...")
            self.authenticated_user = "Development User"
            self.log_authentication_attempt(self.authenticated_user, True)
            return True
        
        # Get user input for bypass phrase (don't speak the prompt for security)
        user_input = self.get_user_input("Bypass phrase", speak_prompt=False)
        
        # Clean the user input and bypass phrase for comparison
        cleaned_input = self.clean_text_for_comparison(user_input)
        cleaned_bypass = self.clean_text_for_comparison(self.bypass_phrase)
        
        print(f"Evaluating bypass.")
        
        if cleaned_input == cleaned_bypass:
            self._speak("Bypass successful!")
            self.authenticated_user = "Bypass User"
            self.log_authentication_attempt(self.authenticated_user, True)
            return True
        else:
            self._speak("Incorrect bypass phrase. Access denied.")
            self.log_authentication_attempt("Unknown User", False)
            return False
    
    def authenticate_with_face(self):
        """
        Authenticate using facial recognition
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        try:
            import cv2
            import face_recognition
        except ImportError:
            logger.warning("Face recognition modules not available")
            self._speak("Face recognition not available. Proceeding to bypass authentication.")
            return False
        
        self._speak("Starting facial recognition authentication...")
        
        # Initialize webcam
        video_capture = None
        try:
            video_capture = cv2.VideoCapture(0)
            if not video_capture.isOpened():
                self._speak("Error: Could not open webcam. Proceeding to bypass authentication.")
                return False
        except Exception as e:
            logger.error(f"Error initializing webcam: {e}")
            self._speak("Error initializing webcam. Proceeding to bypass authentication.")
            return False
        
        # Load the user's face image
        user_image_path = os.path.join(self.auth_dir, "user_face.jpg")
        
        # Check if user image exists
        if not os.path.exists(user_image_path):
            logger.warning(f"User face image not found at {user_image_path}")
            self._speak("User face image not found. Using placeholder for recognition.")
            
            # Create an empty file as placeholder if it doesn't exist
            try:
                with open(user_image_path, 'a'):
                    pass
            except Exception as e:
                logger.error(f"Error creating placeholder: {e}")
        
        # Try to load the face image
        known_face_encoding = None
        try:
            known_image = face_recognition.load_image_file(user_image_path)
            known_face_encodings = face_recognition.face_encodings(known_image)
            if known_face_encodings:
                known_face_encoding = known_face_encodings[0]
            else:
                self._speak("No face detected in the reference image.")
                if video_capture:
                    video_capture.release()
                cv2.destroyAllWindows()
                return False
        except Exception as e:
            logger.error(f"Error loading reference face: {e}")
            self._speak("Error loading reference face.")
            if video_capture:
                video_capture.release()
            cv2.destroyAllWindows()
            return False
        
        self._speak("Looking for your face. Press 'q' to quit authentication...")
        
        # Set authentication timeout
        start_time = time.time()
        
        while True:
            # Check for timeout
            if time.time() - start_time > self.face_timeout:
                self._speak("Authentication timed out.")
                if video_capture:
                    video_capture.release()
                cv2.destroyAllWindows()
                return False
            
            # Capture frame-by-frame
            ret, frame = video_capture.read()
            
            if not ret:
                continue
            
            try:
                # Resize frame for faster face recognition processing
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                
                # Convert the image from BGR color (OpenCV) to RGB color (face_recognition)
                rgb_small_frame = small_frame[:, :, ::-1]
                
                # Find all face locations and face encodings in the current frame
                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                
                # Check if any face matches
                for face_encoding in face_encodings:
                    if known_face_encoding is not None:
                        matches = face_recognition.compare_faces([known_face_encoding], face_encoding)
                        
                        if True in matches:
                            self._speak("Authentication successful: User recognized!")
                            video_capture.release()
                            cv2.destroyAllWindows()
                            self.authenticated_user = "Authorized User"
                            self.log_authentication_attempt(self.authenticated_user, True)
                            return True
            except Exception as e:
                logger.error(f"Error during face recognition: {e}")
            
            # Display the resulting frame with face rectangles
            try:
                for (top, right, bottom, left) in face_locations:
                    # Scale back up face locations since we scaled the frame down
                    top *= 4
                    right *= 4
                    bottom *= 4
                    left *= 4
                    
                    # Draw a box around the face
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                
                # Display the resulting frame
                cv2.imshow('Authentication', frame)
            except Exception as e:
                logger.error(f"Error displaying frame: {e}")
            
            # Break loop with 'q' key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # When everything is done, release the capture
        if video_capture:
            video_capture.release()
        cv2.destroyAllWindows()
        return False
    
    def authenticate_user(self):
        """
        Main authentication flow following the requested process:
        1. Begin Face Authentication
        2. If face auth fails, ask whether to retry face or try bypass phrase
        3. If bypass phrase matches, continue
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        # Check if face recognition is available
        face_recognition_available = False
        try:
            import cv2
            import face_recognition
            face_recognition_available = True
        except ImportError:
            logger.warning("Face recognition modules not available")
            self._speak("Face recognition not available. Proceeding to bypass authentication.")
            return self.handle_bypass()
        
        if not face_recognition_available:
            # Skip directly to bypass authentication if face recognition is not available
            return self.handle_bypass()
        
        # Try facial authentication first
        face_auth_result = self.authenticate_with_face()
        if face_auth_result:
            return True
        
        # Face authentication failed, ask user if they want to retry or try bypass
        choice = self.get_user_input("Face authentication failed. Would you like to retry face authentication or try bypass phrase? (face/bypass)")
        choice_lower = choice.lower()
        
        if "face" in choice_lower or "retry" in choice_lower:
            # Retry face authentication
            face_auth_result = self.authenticate_with_face()
            if face_auth_result:
                return True
            else:
                # Second face attempt failed, go to bypass
                self._speak("Face authentication failed again. Proceeding to bypass authentication.")
                return self.handle_bypass()
        else:
            # Proceed with bypass authentication
            return self.handle_bypass()
    
    def get_authenticated_user(self):
        """Get currently authenticated user"""
        return self.authenticated_user
