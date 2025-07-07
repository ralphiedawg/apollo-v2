import os
from typing import Optional, Tuple
from dotenv import load_dotenv

# Optional imports for face recognition - gracefully handle missing dependencies
try:
    import cv2
    import face_recognition
    import numpy as np
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("⚠ OpenCV and/or face_recognition not available. Face recognition will be disabled.")
    print("  Only bypass phrase authentication will be available.")
    print("  To enable face recognition, install: pip install opencv-python face_recognition")

class FaceAuthenticator:
    """
    Face recognition authentication system for Apollo home assistant.
    """
    
    def __init__(self, face_images_dir: str = "face_images"):
        """
        Initialize the face authenticator.
        
        Args:
            face_images_dir: Directory containing authorized face images
        """
        self.face_images_dir = face_images_dir
        self.authorized_encodings = []
        self.authorized_names = []
        
        # Load environment variables
        load_dotenv()
        self.bypass_phrase = os.getenv("AUTH_BYPASS", "apollo override alpha seven")
        
        # Create face images directory if it doesn't exist
        os.makedirs(self.face_images_dir, exist_ok=True)
        
        # Create placeholder image if no authorized faces exist
        self._create_placeholder_if_needed()
        
        # Load authorized face encodings
        self._load_authorized_faces()
    
    def _create_placeholder_if_needed(self):
        """Create a placeholder face image if no authorized faces exist."""
        placeholder_path = os.path.join(self.face_images_dir, "placeholder.txt")
        
        # Check if any image files exist
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        has_images = any(
            f.lower().endswith(ext) for ext in image_extensions
            for f in os.listdir(self.face_images_dir) if os.path.isfile(os.path.join(self.face_images_dir, f))
        )
        
        if not has_images and not os.path.exists(placeholder_path):
            with open(placeholder_path, 'w') as f:
                f.write("""
FACE IMAGE PLACEHOLDER

To enable face recognition authentication:
1. Add your face image(s) to this directory
2. Supported formats: .jpg, .jpeg, .png, .bmp
3. Name the file with your name (e.g., "ralph.jpg")
4. The system will automatically detect and use your face for authentication

Until you add face images, you can use the bypass phrase from the .env file.
""")
    
    def _load_authorized_faces(self):
        """Load and encode authorized face images."""
        self.authorized_encodings = []
        self.authorized_names = []
        
        if not FACE_RECOGNITION_AVAILABLE:
            print("⚠ Face recognition not available. Skipping face loading.")
            return
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        
        for filename in os.listdir(self.face_images_dir):
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                image_path = os.path.join(self.face_images_dir, filename)
                
                try:
                    # Load the image
                    image = face_recognition.load_image_file(image_path)
                    
                    # Get face encodings
                    encodings = face_recognition.face_encodings(image)
                    
                    if encodings:
                        # Use the first face found in the image
                        self.authorized_encodings.append(encodings[0])
                        # Use filename without extension as name
                        name = os.path.splitext(filename)[0]
                        self.authorized_names.append(name)
                        print(f"✓ Loaded authorized face: {name}")
                    else:
                        print(f"⚠ No face found in image: {filename}")
                        
                except Exception as e:
                    print(f"✗ Error loading face image {filename}: {e}")
    
    def authenticate_with_camera(self, timeout: int = 10) -> Tuple[bool, Optional[str]]:
        """
        Authenticate user using camera face recognition.
        
        Args:
            timeout: Maximum seconds to wait for face recognition
            
        Returns:
            Tuple of (success, recognized_name)
        """
        if not FACE_RECOGNITION_AVAILABLE:
            print("⚠ Face recognition not available. Skipping camera authentication.")
            return False, None
            
        if not self.authorized_encodings:
            print("⚠ No authorized faces loaded. Authentication will require bypass phrase.")
            return False, None
        
        print("🔍 Starting face recognition authentication...")
        print("👤 Please look at the camera. Press 'q' to quit.")
        
        # Initialize camera
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("✗ Error: Could not open camera")
            return False, None
        
        frame_count = 0
        max_frames = timeout * 10  # Assuming ~10 FPS
        
        try:
            while frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    print("✗ Error: Could not read frame from camera")
                    break
                
                frame_count += 1
                
                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Find faces in the frame
                face_locations = face_recognition.face_locations(rgb_frame)
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                
                # Check each face against authorized faces
                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces(
                        self.authorized_encodings, face_encoding, tolerance=0.6
                    )
                    
                    if True in matches:
                        # Face recognized
                        match_index = matches.index(True)
                        name = self.authorized_names[match_index]
                        print(f"✓ Face recognized: {name}")
                        cap.release()
                        cv2.destroyAllWindows()
                        return True, name
                
                # Display frame with face detection
                for (top, right, bottom, left) in face_locations:
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                
                cv2.imshow('Apollo Face Authentication', frame)
                
                # Check for 'q' key press
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("Face recognition cancelled by user.")
                    break
                    
        except Exception as e:
            print(f"✗ Error during face recognition: {e}")
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
        
        print("⚠ Face recognition timeout or cancelled.")
        return False, None
    
    def verify_bypass_phrase(self, user_input: str) -> bool:
        """
        Verify the bypass phrase.
        
        Args:
            user_input: The phrase entered by the user
            
        Returns:
            True if the bypass phrase is correct
        """
        return user_input.strip().lower() == self.bypass_phrase.strip().lower()
    
    def authenticate(self, enable_voice_input: bool = False, whisper_capture=None) -> bool:
        """
        Main authentication method that tries face recognition first, then bypass phrase.
        
        Args:
            enable_voice_input: Whether voice input is enabled
            whisper_capture: WhisperCapture instance for voice input
            
        Returns:
            True if authentication is successful
        """
        # Try face recognition first
        print("\n🔐 Apollo Authentication System")
        print("=" * 40)
        
        success, recognized_name = self.authenticate_with_camera()
        
        if success:
            print(f"🎉 Welcome back, {recognized_name}!")
            return True
        
        # Face recognition failed, try bypass phrase
        print("\n🔑 Face recognition failed. Please enter the bypass phrase:")
        
        max_attempts = 3
        for attempt in range(max_attempts):
            print(f"\nAttempt {attempt + 1}/{max_attempts}")
            
            if enable_voice_input and whisper_capture:
                print("🎤 Say the bypass phrase (or type 'manual' to switch to keyboard):")
                
                try:
                    user_input = whisper_capture.listen_and_transcribe()
                    if user_input is None or user_input.strip().lower() == "manual":
                        user_input = input("Enter bypass phrase: ")
                    else:
                        print(f"You said: {user_input}")
                except Exception as e:
                    print(f"Voice input error: {e}")
                    user_input = input("Enter bypass phrase: ")
            else:
                user_input = input("Enter bypass phrase: ")
            
            if self.verify_bypass_phrase(user_input):
                print("✓ Bypass phrase accepted. Authentication successful!")
                return True
            else:
                print("✗ Incorrect bypass phrase.")
        
        print("🚫 Authentication failed after 3 attempts.")
        return False