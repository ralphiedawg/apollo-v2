"""
Authentication Flow Module for Apollo

This module handles the complete authentication process including
face recognition and bypass phrase validation.
"""

import os
import logging
from typing import Optional
from .face_recognition_auth import FaceRecognitionAuth

class AuthenticationFlow:
    """
    Complete authentication flow for Apollo.
    
    Handles face recognition and bypass phrase authentication.
    """
    
    def __init__(self, authorized_face_path: str = "authorized_user.jpg"):
        """
        Initialize the authentication flow.
        
        Args:
            authorized_face_path (str): Path to authorized user's face image
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize face recognition
        self.face_auth = FaceRecognitionAuth(authorized_face_path)
        
        # Get bypass phrase from environment or .env file
        self.bypass_phrase = self._load_bypass_phrase()
        
        if not self.bypass_phrase:
            self.logger.warning("No AUTH_BYPASS phrase found in environment")
    
    def _load_bypass_phrase(self) -> str:
        """
        Load bypass phrase from environment or .env file.
        
        Returns:
            str: Bypass phrase
        """
        # First try environment variable
        bypass_phrase = os.getenv("AUTH_BYPASS")
        if bypass_phrase:
            return bypass_phrase
        
        # Try to load from .env file
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("AUTH_BYPASS="):
                            return line.split("=", 1)[1].strip()
            except Exception as e:
                self.logger.error(f"Error reading .env file: {e}")
        
        # Default fallback
        return "apollo_master_key"
    
    def authenticate_user(self, enable_voice_input: bool = False, whisper_capture=None, apollotts=None) -> bool:
        """
        Perform complete user authentication.
        
        Args:
            enable_voice_input (bool): Whether voice input is enabled
            whisper_capture: WhisperCapture instance for voice input
            apollotts: ApolloTTS instance for speech output
            
        Returns:
            bool: True if authentication successful, False otherwise
        """
        print("\n=== Apollo Authentication System ===")
        
        # Step 1: Try face recognition
        print("Step 1: Face Recognition")
        if self.face_auth.authenticate_face():
            print("✓ Face recognition successful!")
            return True
        
        # Step 2: Face recognition failed, try bypass phrase
        print("✗ Face recognition failed or unavailable")
        print("\nStep 2: Bypass Phrase Authentication")
        
        return self._handle_bypass_authentication(enable_voice_input, whisper_capture, apollotts)
    
    def _handle_bypass_authentication(self, enable_voice_input: bool, whisper_capture=None, apollotts=None) -> bool:
        """
        Handle bypass phrase authentication.
        
        Args:
            enable_voice_input (bool): Whether voice input is enabled
            whisper_capture: WhisperCapture instance for voice input
            apollotts: ApolloTTS instance for speech output
            
        Returns:
            bool: True if bypass phrase is correct, False otherwise
        """
        alert_message = "User not authorized, please input a bypass phrase"
        print(f"\n🔒 {alert_message}")
        
        # Speak the alert if TTS is enabled
        if apollotts:
            apollotts.speak(alert_message)
        
        # Get bypass phrase from user
        for attempt in range(3):  # Allow 3 attempts
            if enable_voice_input and whisper_capture:
                bypass_input = self._get_voice_input(whisper_capture)
            else:
                bypass_input = self._get_text_input()
            
            if bypass_input and self._validate_bypass_phrase(bypass_input):
                success_message = "✓ Bypass phrase accepted. Welcome to Apollo!"
                print(success_message)
                if apollotts:
                    apollotts.speak("Bypass phrase accepted. Welcome to Apollo!")
                return True
            else:
                attempts_left = 2 - attempt
                if attempts_left > 0:
                    fail_message = f"✗ Incorrect bypass phrase. {attempts_left} attempts remaining."
                    print(fail_message)
                    if apollotts:
                        apollotts.speak(f"Incorrect bypass phrase. {attempts_left} attempts remaining.")
                else:
                    fail_message = "✗ Maximum attempts exceeded. Access denied."
                    print(fail_message)
                    if apollotts:
                        apollotts.speak("Maximum attempts exceeded. Access denied.")
        
        return False
    
    def _get_voice_input(self, whisper_capture) -> Optional[str]:
        """
        Get bypass phrase via voice input.
        
        Args:
            whisper_capture: WhisperCapture instance
            
        Returns:
            str: User's voice input or None if failed
        """
        print("🎤 Please say the bypass phrase:")
        try:
            voice_input = whisper_capture.listen_and_transcribe()
            if voice_input:
                print(f"Voice input received: {voice_input}")
                return voice_input.strip()
            else:
                print("No voice input detected")
                return None
        except Exception as e:
            self.logger.error(f"Voice input error: {e}")
            print("Voice input failed, please try again")
            return None
    
    def _get_text_input(self) -> Optional[str]:
        """
        Get bypass phrase via text input.
        
        Returns:
            str: User's text input or None if cancelled
        """
        try:
            text_input = input("🔑 Enter bypass phrase: ").strip()
            return text_input if text_input else None
        except (KeyboardInterrupt, EOFError):
            print("\nInput cancelled")
            return None
    
    def _validate_bypass_phrase(self, user_input: str) -> bool:
        """
        Validate the bypass phrase.
        
        Args:
            user_input (str): User's input phrase
            
        Returns:
            bool: True if phrase is correct, False otherwise
        """
        if not user_input or not self.bypass_phrase:
            return False
        
        # Case-insensitive comparison
        return user_input.lower().strip() == self.bypass_phrase.lower().strip()