#!/usr/bin/env python3
"""
Test script for face authentication module.
Tests the bypass phrase functionality without requiring OpenCV.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.auth.face_authenticator import FaceAuthenticator

def test_bypass_phrase():
    """Test the bypass phrase functionality"""
    print("Testing Face Authentication Module")
    print("=" * 40)
    
    # Create authenticator
    auth = FaceAuthenticator()
    
    # Test correct bypass phrase
    correct_phrase = "apollo override alpha seven"
    print(f"Testing correct phrase: '{correct_phrase}'")
    result = auth.verify_bypass_phrase(correct_phrase)
    print(f"Result: {'✓ PASS' if result else '✗ FAIL'}")
    
    # Test incorrect bypass phrase
    incorrect_phrase = "wrong phrase"
    print(f"\nTesting incorrect phrase: '{incorrect_phrase}'")
    result = auth.verify_bypass_phrase(incorrect_phrase)
    print(f"Result: {'✓ PASS' if not result else '✗ FAIL'}")
    
    # Test case insensitive
    mixed_case_phrase = "APOLLO Override Alpha Seven"
    print(f"\nTesting mixed case phrase: '{mixed_case_phrase}'")
    result = auth.verify_bypass_phrase(mixed_case_phrase)
    print(f"Result: {'✓ PASS' if result else '✗ FAIL'}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_bypass_phrase()