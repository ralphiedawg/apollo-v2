#!/usr/bin/env python3
"""
Demo script showing the Apollo Face Authentication System.
This demonstrates how the authentication system works.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.auth.face_authenticator import FaceAuthenticator

def demo_authentication():
    """Demo the authentication system"""
    print("🚀 Apollo Face Authentication System Demo")
    print("=" * 50)
    
    # Initialize the authentication system
    print("\n1. Initializing Authentication System...")
    face_auth = FaceAuthenticator()
    
    # Show current configuration
    print(f"   Face images directory: face_images/")
    print(f"   Bypass phrase: '{face_auth.bypass_phrase}'")
    print(f"   OpenCV available: {face_auth.__class__.__module__.startswith('core.auth') and 'FACE_RECOGNITION_AVAILABLE' in globals()}")
    
    # Demo directory structure
    print("\n2. Directory Structure:")
    if os.path.exists("face_images"):
        files = os.listdir("face_images")
        for file in files:
            print(f"   📁 face_images/{file}")
    
    # Demo bypass phrase authentication
    print("\n3. Authentication Methods:")
    print("   🔍 Face Recognition: Available when OpenCV is installed")
    print("   🔑 Bypass Phrase: Always available")
    
    # Demo bypass phrase testing
    print("\n4. Bypass Phrase Testing:")
    test_phrases = [
        "apollo override alpha seven",  # Correct
        "APOLLO OVERRIDE ALPHA SEVEN",  # Correct (case insensitive)
        "wrong phrase",  # Incorrect
        "apollo override alpha seven ",  # Correct (with trailing space)
    ]
    
    for phrase in test_phrases:
        result = face_auth.verify_bypass_phrase(phrase)
        status = "✓ ACCEPT" if result else "✗ REJECT"
        print(f"   '{phrase}' -> {status}")
    
    # Demo integration points
    print("\n5. Integration Points:")
    print("   • main.py calls face_auth.authenticate(enable_voice_input, whisper_capture)")
    print("   • Supports both text and voice input for bypass phrase")
    print("   • Gracefully handles missing OpenCV/face_recognition dependencies")
    print("   • Returns True/False for authentication success")
    
    print("\n6. Usage Instructions:")
    print("   For Face Recognition:")
    print("   • Install dependencies: pip install opencv-python face_recognition")
    print("   • Add face images to face_images/ directory")
    print("   • Name images with your name (e.g., ralph.jpg)")
    print("   • System will automatically detect and use faces")
    
    print("\n   For Bypass Phrase:")
    print("   • Use the phrase from .env file: AUTH_BYPASS")
    print("   • Works with both text and voice input")
    print("   • Case insensitive matching")
    print("   • Supports leading/trailing whitespace")
    
    print("\n" + "=" * 50)
    print("🎉 Demo completed! Authentication system is ready.")
    print("=" * 50)

if __name__ == "__main__":
    demo_authentication()