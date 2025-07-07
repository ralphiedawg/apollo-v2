import torch
import numpy as np
import speech_recognition as sr
from faster_whisper import WhisperModel
import tempfile
import os
import time
import threading

class WhisperCapture:
    def __init__(self, model_size="base", pause_threshold=2.0):
        """
        Initialize the WhisperCapture with a specified model size.
        
        Parameters:
            model_size (str): Size of the Whisper model to use. Options: "tiny", "base", "small", "medium", "large"
            pause_threshold (float): How long (in seconds) to wait during a pause before considering the phrase complete
        """
        self.model_size = model_size
        print(f"Loading Whisper model ({model_size})...")
        
        # Use CPU by default, but use CUDA if available
        compute_type = "float16" if torch.cuda.is_available() else "int8"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Initialize the model
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print(f"Whisper model loaded successfully on {device}!")
        self.recognizer = sr.Recognizer()
        
        # Flag to track if TTS is playing - to prevent feedback
        self.is_speaking = False
        
        # Parameters for voice activity detection
        self.energy_threshold = 1000      # Default energy threshold for silence detection
        self.pause_threshold = pause_threshold  # How long a pause needs to be to consider the phrase complete
        self.dynamic_energy_threshold = True   # Automatically adjust for ambient noise
        
    def set_speaking_state(self, is_speaking):
        """Set the speaking state to prevent recording while TTS is active"""
        self.is_speaking = is_speaking
        
    def wait_for_silence(self, timeout=2.0):
        """Wait until no speech is detected for a specified time"""
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # Check energy levels
                    audio = self.recognizer.listen(source, timeout=0.3, phrase_time_limit=0.3)
                    time.sleep(0.1)
                except sr.WaitTimeoutError:
                    # No speech detected in this sample
                    return True
            return True  # Return True after timeout anyway
        
    def capture_audio(self):
        """Capture audio from the microphone and return it."""
        # Wait a moment after TTS has finished to avoid feedback
        if self.is_speaking:
            print("Waiting for TTS to finish...")
            while self.is_speaking:
                time.sleep(0.1)
            time.sleep(0.5)  # Additional delay after TTS stops
            
            # Wait for silence before starting to listen
            self.wait_for_silence()
            
        with sr.Microphone() as source:
            print("Listening...")
            # Adjust for ambient noise before recording
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            self.recognizer.energy_threshold = self.energy_threshold
            self.recognizer.pause_threshold = self.pause_threshold
            self.recognizer.dynamic_energy_threshold = self.dynamic_energy_threshold
            
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=30)
                print("Audio captured!")
                return audio
            except sr.WaitTimeoutError:
                print("No speech detected within timeout period.")
                return None
    
    def recognize_speech(self, audio):
        """
        Convert speech to text using Whisper.
        
        Parameters:
            audio: Audio data from speech_recognition
            
        Returns:
            str: Transcribed text or None if transcription fails
        """
        if audio is None:
            return None
            
        try:
            # Need to convert speech_recognition audio to format whisper can use
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_path = temp_audio.name
                with open(temp_path, "wb") as f:
                    f.write(audio.get_wav_data())
            
            # Transcribe the audio using Whisper
            segments, info = self.model.transcribe(temp_path, beam_size=5)
            os.remove(temp_path)
            
            # Combine all segments into one text
            transcribed_text = " ".join(segment.text for segment in segments)
            
            if transcribed_text:
                print(f"Whisper heard: {transcribed_text}")
                return transcribed_text
            else:
                print("Couldn't understand audio")
                return None
                
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None

    def listen_and_transcribe(self):
        """Convenience method to capture and transcribe audio in one step."""
        audio = self.capture_audio()
        return self.recognize_speech(audio)


if __name__ == "__main__":
    # Test the WhisperCapture
    whisper_capture = WhisperCapture()
    text = whisper_capture.listen_and_transcribe()
    print(f"Transcribed: {text}")
