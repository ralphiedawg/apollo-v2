import torch
from TTS.api import TTS
import subprocess
from core.tts.playaudio import play_audio

class ApolloTTS:
    def __init__(self, model_name="tts_models/en/vctk/vits", speaker_id="p273"):
        # Automatically selects device, MPS for Mac, CUDA for Nvidia, fallback to CPU
        self.device = "mps" if torch.backends.mps.is_available() else \
                      "cuda" if torch.cuda.is_available() else \
                      "cpu"
        
        self.tts = TTS(model_name)
        self.tts.to(self.device)

        self.speaker_id = speaker_id if self.tts.is_multi_speaker else None

    def speak(self, given_text="This is a demo", output_dir="cache"):
        self.tts.tts_to_file(
            text=given_text,
            speaker=self.speaker_id,
            file_path=f"{output_dir}/output.wav"
        )
        play_audio("cache/output.wav", 1)

    def speak_to_file(self, given_text="This is a demo", output_path="cache/output.wav"):
        self.tts.tts_to_file(
            text=given_text,
            speaker=self.speaker_id,
            file_path=output_path
        )

if __name__ == "__main__":
    apollotts = ApolloTTS()
    apollotts.speak(given_text = "Hello, I'm Apollo, your personal home assistant", output_dir = "cache")
    subprocess.run(["afplay", "cache/output.wav"])
