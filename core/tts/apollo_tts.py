import torch
from TTS.api import TTS
import subprocess
from core.tts.playaudio import play_audio
import threading

class ApolloTTS:
    def __init__(self, model_name="tts_models/en/vctk/vits", speaker_id="p273"):
        # Automatically selects device, MPS for Mac, CUDA for Nvidia, fallback to CPU
        self.device = "mps" if torch.backends.mps.is_available() else \
                     "cuda" if torch.cuda.is_available() else \
                     "cpu"
        
        self.tts = TTS(model_name)
        self.tts.to(self.device)

        self.speaker_id = speaker_id if self.tts.is_multi_speaker else None
        
        # For tracking speaking state
        self.is_speaking = False
        self.whisper_capture = None  # Will be set by main.py
        
    def set_whisper_capture(self, whisper_capture):
        """Set the WhisperCapture instance to coordinate speaking/listening"""
        self.whisper_capture = whisper_capture

    def speak(self, given_text="This is a demo", output_dir="cache"):
        """Generate speech and play it, signaling when speaking starts and ends"""
        if self.whisper_capture:
            self.whisper_capture.set_speaking_state(True)
            self.is_speaking = True
        
        self.tts.tts_to_file(
            text=given_text,
            speaker=self.speaker_id,
            file_path=f"{output_dir}/output.wav"
        )
        
        # Play audio in a separate thread so we can update the speaking state when done
        def play_and_signal_done():
            play_audio("cache/output.wav", 1)
            if self.whisper_capture:
                self.whisper_capture.set_speaking_state(False)
                self.is_speaking = False
        
        thread = threading.Thread(target=play_and_signal_done)
        thread.start()

    def speak_to_file(self, given_text="This is a demo", output_path="cache/output.wav"):
        self.tts.tts_to_file(
            text=given_text,
            speaker=self.speaker_id,
            file_path=output_path
        )
