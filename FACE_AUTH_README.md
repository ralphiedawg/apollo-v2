# Apollo Face Authentication System

The Apollo home assistant now includes a face recognition authentication system that provides secure access using either face recognition or a bypass phrase.

## Features

- **Face Recognition**: Uses OpenCV and face_recognition library for camera-based authentication
- **Bypass Phrase**: Secure text/voice-based authentication using a configurable phrase
- **Voice Input Support**: Works with both text and speech-to-text input
- **Graceful Degradation**: Functions even without OpenCV dependencies
- **Case Insensitive**: Bypass phrase matching is case insensitive
- **Automatic Setup**: Creates necessary directories and placeholder files

## Installation

### Basic Setup (Bypass Phrase Only)
```bash
pip install python-dotenv
```

### Full Setup (Face Recognition + Bypass Phrase)
```bash
pip install python-dotenv opencv-python face_recognition
```

## Configuration

### Environment Variables
Create or edit `.env` file in the project root:
```
AUTH_BYPASS=your_secure_bypass_phrase_here
```

### Face Images
1. Add face images to the `face_images/` directory
2. Supported formats: .jpg, .jpeg, .png, .bmp
3. Name files with the person's name (e.g., "ralph.jpg")
4. The system automatically detects and loads faces

## Usage

### In Main Application
The authentication system is automatically integrated into the main Apollo application:

```python
from core.auth.face_authenticator import FaceAuthenticator

# Initialize authenticator
face_auth = FaceAuthenticator()

# Authenticate user (supports both text and voice input)
if face_auth.authenticate(enable_voice_input, whisper_capture):
    # User authenticated successfully
    print("Welcome to Apollo!")
else:
    # Authentication failed
    print("Authentication failed")
```

### Authentication Flow
1. **Face Recognition**: Attempts to recognize face using camera
2. **Bypass Phrase**: If face recognition fails, prompts for bypass phrase
3. **Voice/Text Input**: Supports both speech-to-text and keyboard input
4. **Multiple Attempts**: Allows up to 3 attempts for bypass phrase

## API Reference

### FaceAuthenticator Class

#### `__init__(face_images_dir="face_images")`
Initialize the face authenticator.

#### `authenticate(enable_voice_input=False, whisper_capture=None)`
Main authentication method. Returns `True` if authentication succeeds.

#### `authenticate_with_camera(timeout=10)`
Attempts face recognition using camera. Returns `(success, recognized_name)`.

#### `verify_bypass_phrase(user_input)`
Verifies the bypass phrase. Returns `True` if correct.

## Directory Structure

```
apollo-v2/
├── core/
│   └── auth/
│       ├── __init__.py
│       └── face_authenticator.py
├── face_images/
│   └── placeholder.txt
├── .env
└── main.py
```

## Security Considerations

- **Bypass Phrase**: Store securely in `.env` file
- **Face Images**: Keep face images in secure directory
- **Camera Access**: System requests camera access for face recognition
- **Graceful Failure**: System continues to function even if dependencies are missing

## Troubleshooting

### OpenCV Not Available
If you see warnings about OpenCV not being available:
```bash
pip install opencv-python face_recognition
```

### Camera Access Issues
- Ensure camera is not being used by another application
- Check camera permissions for the terminal/application
- Try running with elevated permissions if needed

### Face Recognition Not Working
- Ensure good lighting when taking face images
- Use clear, front-facing photos
- Check image formats are supported (.jpg, .jpeg, .png, .bmp)
- Verify face is clearly visible in the image

## Testing

Several test scripts are available:
- `test_auth.py`: Basic authentication functionality
- `test_voice_auth.py`: Voice input authentication
- `test_main_integration.py`: Integration testing
- `demo_auth.py`: Complete demonstration

Run tests with:
```bash
python demo_auth.py
```

## Integration with Apollo

The authentication system is seamlessly integrated into the Apollo main application:

1. User configures speech synthesis and voice input
2. Authentication system initializes
3. Face recognition attempts authentication
4. On failure, prompts for bypass phrase
5. Supports both text and voice input for bypass phrase
6. On success, proceeds to main Apollo chat loop
7. On failure, exits application

This provides a secure, user-friendly authentication flow that maintains the existing Apollo user experience while adding robust security features.