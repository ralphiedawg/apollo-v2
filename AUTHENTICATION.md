# Apollo V2 Face Recognition Authentication System

This document describes the face recognition authentication system implemented for Apollo V2.

## Overview

The authentication system provides secure access to Apollo through face recognition with a bypass phrase fallback. It integrates seamlessly with the existing Apollo architecture and supports both speech synthesis and voice input modes.

## Features

- **Face Recognition**: Primary authentication method using OpenCV and face_recognition library
- **Bypass Phrase**: Fallback authentication method with configurable phrase
- **Speech Integration**: Works with Apollo's TTS and STT systems
- **Placeholder Implementation**: System works without face recognition dependencies
- **Environment Configuration**: Bypass phrase configurable via .env file

## Architecture

### Core Components

1. **FaceRecognitionAuth** (`core/auth/face_recognition_auth.py`)
   - Handles face recognition functionality
   - Graceful fallback when dependencies are unavailable
   - Webcam integration for live face detection

2. **AuthenticationFlow** (`core/auth/authentication_flow.py`)
   - Orchestrates the complete authentication process
   - Manages face recognition → bypass phrase flow
   - Integrates with speech synthesis and voice input

3. **Environment Configuration** (`.env`)
   - Stores the bypass phrase securely
   - Other configuration options

## Integration

The authentication system is integrated into `main.py` after the user selects speech synthesis and voice input options but before the main chat loop begins.

### Authentication Flow

1. **Setup Phase**: User configures speech synthesis and voice input
2. **Face Recognition**: System attempts to recognize authorized user's face
3. **Bypass Authentication**: If face recognition fails, system prompts for bypass phrase
4. **Access Control**: Successful authentication proceeds to chat loop, failure exits

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
AUTH_BYPASS=your_secure_bypass_phrase_here
```

### Face Recognition Setup

1. Place authorized user's photo as `authorized_user.jpg` in the project root
2. Install face recognition dependencies:
   ```bash
   pip install opencv-python face-recognition
   ```

### Dependencies

The system works in two modes:

**Full Mode** (with face recognition):
- `opencv-python>=4.10.0.84`
- `face-recognition>=1.3.0`

**Placeholder Mode** (bypass phrase only):
- No additional dependencies required

## Usage

### Running the System

The authentication system is automatically invoked when running Apollo:

```bash
python main.py
```

### Authentication Process

1. Configure speech synthesis and voice input options
2. System will attempt face recognition
3. If face not recognized, enter bypass phrase when prompted
4. System supports both text and voice input for bypass phrase

### Testing

Run the test scripts to verify functionality:

```bash
# Basic authentication test
python /tmp/test_auth.py

# Integration test
python /tmp/test_integration.py

# Interactive demo
python /tmp/demo_auth.py
```

## Security Considerations

1. **Bypass Phrase**: Store securely in `.env` file, never in code
2. **Face Image**: Protect the authorized user's face image file
3. **Access Attempts**: System limits bypass phrase attempts to 3
4. **Environment**: Use strong, unique bypass phrases

## Troubleshooting

### Common Issues

1. **Face recognition not working**: Check if camera is accessible and dependencies are installed
2. **Bypass phrase not accepted**: Verify .env file configuration and phrase spelling
3. **Import errors**: Ensure all modules are in the correct directory structure

### Logs

The system uses Python's logging module. Enable debug logging to see detailed authentication flow:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

1. **Multiple Users**: Support for multiple authorized faces
2. **Biometric Integration**: Support for fingerprint readers
3. **Advanced Security**: Time-based access tokens
4. **Audit Logging**: Detailed access attempt logging
5. **Remote Authentication**: Network-based authentication options

## Implementation Notes

- The system uses a placeholder implementation when face recognition dependencies are unavailable
- Face recognition attempts are limited to 10 seconds to prevent hanging
- The bypass phrase comparison is case-insensitive
- Speech synthesis provides audio feedback for authentication status
- Voice input is supported for bypass phrase entry