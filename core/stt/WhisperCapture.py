import torch
import numpy as np
import pyaudio
import webrtcvad
import wave
import os
import time
import threading
from queue import Queue
import cv2  # For camera device listing
from faster_whisper import WhisperModel

class WhisperCapture:
    def __init__(self, model_size="base", pause_threshold=2.0):
        """
        Initialize the WhisperCapture for voice recognition
        
        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            pause_threshold: Seconds of silence to consider end of speech
        """
        self.model_size = model_size
        self.pause_threshold = pause_threshold
        self.audio_queue = Queue()
        self.is_paused = False
        
        # Flag to track if TTS is playing - to prevent feedback
        self.is_speaking = False
        
        # Timeout settings
        self.speaking_timeout = 60.0  # Maximum time to wait for TTS to complete
        
        # Stream reference
        self.stream = None
        
        # Initialize VAD
        self.vad = webrtcvad.Vad(3)  # Aggressiveness level 3 (most aggressive)
        
        # Whisper settings
        self.sample_rate = 16000
        self.channels = 1
        self.format = pyaudio.paInt16
        self.chunk_size = 480  # 30ms at 16kHz, must be 10, 20, or 30ms for VAD
        
        # Initialize faster-whisper model
        print(f"Loading faster-whisper {model_size} model...")
        # Use CPU by default, but use CUDA if available
        compute_type = "float16" if torch.cuda.is_available() else "int8"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Initialize the model
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print(f"faster-whisper model loaded successfully on {device}!")
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
    
    def set_speaking_state(self, is_speaking):
        """Set the speaking state to prevent recording while TTS is active"""
        self.is_speaking = is_speaking
        # Automatically pause/resume listening based on speaking state
        if is_speaking:
            self.pause_listening()
        else:
            # Add a small delay before resuming to ensure audio output has stopped
            time.sleep(0.3)
            self.resume_listening()
        
    def pause_listening(self):
        """Pause the listening to prevent feedback loops"""
        self.is_paused = True
        
    def resume_listening(self):
        """Resume listening after pausing"""
        self.is_paused = False
        # Clear any audio that might have been captured while paused
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except:
                pass
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for PyAudio to receive audio data"""
        if not self.is_paused and not self.is_speaking:
            self.audio_queue.put(in_data)
        return (in_data, pyaudio.paContinue)
    
    def _stop_stream_safely(self):
        """Safely stop and close the audio stream"""
        try:
            if hasattr(self, 'stream') and self.stream:
                if hasattr(self.stream, 'is_active') and self.stream.is_active():
                    try:
                        self.stream.stop_stream()
                    except Exception as e:
                        print(f"Warning: Error stopping stream: {e}")
                try:
                    self.stream.close()
                except Exception as e:
                    print(f"Warning: Error closing stream: {e}")
                self.stream = None
        except Exception as e:
            print(f"Warning: Error closing audio stream: {e}")
    
    def listen_and_transcribe(self):
        """
        Listen for speech and return the transcription.
        Returns None if no speech detected or processing failed.
        """
        # Safely stop any existing stream first
        self._stop_stream_safely()
            
        self.is_paused = False
        self.audio_queue = Queue()
        
        # Wait if TTS is speaking, but with a timeout
        if self.is_speaking:
            print("TTS is active. Waiting for it to finish...")
            start_wait_time = time.time()
            
            while self.is_speaking:
                # Check if we've waited too long
                if time.time() - start_wait_time > self.speaking_timeout:
                    print(f"Warning: TTS speaking state didn't reset after {self.speaking_timeout}s")
                    # Force it to false since something might have gone wrong
                    self.is_speaking = False
                    break
                
                # Wait a bit before checking again
                time.sleep(0.1)
            
            # Add a delay after TTS stops to avoid feedback
            print("TTS finished. Adding delay before listening...")
            time.sleep(0.5)
        
        try:
            # Open the input stream with callback
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            print("Listening... (Press Ctrl+C to stop)")
            
            frames = []
            silent_chunks = 0
            max_silent_chunks = int(self.pause_threshold * (self.sample_rate / self.chunk_size))
            has_speech = False
            
            # Start listening for input
            self.stream.start_stream()
            
            # Listen until we detect enough silence after speech
            start_listen_time = time.time()
            listen_timeout = 25 # Maximum time to wait for initial speech
            
            while True:
                # Check if we need to exit due to a long wait for initial speech
                if not has_speech and time.time() - start_listen_time > listen_timeout:
                    print("No speech detected within timeout period")
                    self._stop_stream_safely()
                    return None
                
                if self.is_paused or self.is_speaking:
                    # If paused or TTS is active, don't process audio but don't block completely
                    time.sleep(0.1)
                    continue
                    
                # Get audio chunk from queue with timeout
                try:
                    audio_data = self.audio_queue.get(timeout=0.5)
                except:
                    continue
                
                # Add frame to our recording
                frames.append(audio_data)
                
                # Check if this chunk has voice activity
                try:
                    is_speech = self.vad.is_speech(audio_data, self.sample_rate)
                except Exception as e:
                    # Some audio frames might cause VAD to fail
                    print(f"VAD error (non-critical): {e}")
                    is_speech = False
                
                if is_speech:
                    has_speech = True
                    silent_chunks = 0
                    # If this is the first speech detected, reset the timer
                    if len(frames) <= 10:  # Just started detecting speech
                        start_listen_time = time.time()  # Reset timeout counter when speech starts
                else:
                    silent_chunks += 1
                
                # If we've had speech and then enough silence, stop recording
                if has_speech and silent_chunks > max_silent_chunks:
                    break
                
                # If no speech and we've been listening for a while, give up
                if not has_speech and len(frames) > 30 * max_silent_chunks:
                    print("No speech detected")
                    self._stop_stream_safely()
                    return None
            
            # Stop the stream
            self._stop_stream_safely()
            
            # If we didn't capture enough audio or no speech was detected
            if not frames or not has_speech:
                return None
                
            print("Processing speech...")
            
            # Convert audio to numpy array
            audio_data = b''.join(frames)
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Transcribe with faster-whisper
            segments, info = self.model.transcribe(audio_np, beam_size=5, language="en")
            
            # Combine all segments into one text
            transcription = " ".join(segment.text for segment in segments)
            
            if transcription:
                print(f"Heard: {transcription}")
                return transcription.strip()
            return None
            
        except KeyboardInterrupt:
            print("Listening stopped by user")
            self._stop_stream_safely()
            return None
        except Exception as e:
            print(f"Error in speech recognition: {e}")
            self._stop_stream_safely()
            return None
            
    def recognize_speech(self, audio):
        """
        Recognize speech from a pre-recorded audio
        
        Args:
            audio: Audio file or binary data
            
        Returns:
            Transcription text or None if failed
        """
        try:
            # Convert to numpy array if needed
            if isinstance(audio, bytes):
                audio_np = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
            else:
                audio_np = audio
                
            # Transcribe with faster-whisper
            segments, info = self.model.transcribe(audio_np, beam_size=5, language="en")
            
            # Combine all segments into one text
            transcription = " ".join(segment.text for segment in segments)
            
            if transcription:
                return transcription.strip()
            return None
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None
    
    def wait_for_silence(self, timeout=2.0):
        """Wait until no speech is detected for a specified time"""
        stream = None
        try:
            # Open a temporary stream to monitor audio levels
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Read audio data
                audio_data = stream.read(self.chunk_size, exception_on_overflow=False)
                
                # Convert to numpy array and calculate RMS energy
                samples = np.frombuffer(audio_data, dtype=np.int16)
                rms = np.sqrt(np.mean(np.square(samples.astype(np.float32))))
                
                # Check if energy is below threshold
                if rms > 500:  # Adjust threshold as needed
                    # Reset timer if we detect sound
                    start_time = time.time()
                    
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error monitoring audio: {e}")
        finally:
            # Cleanup
            if stream:
                try:
                    if stream.is_active():
                        stream.stop_stream()
                    stream.close()
                except Exception as e:
                    print(f"Error closing monitor stream: {e}")
        
        return True
    
    @staticmethod
    def list_camera_devices():
        """
        List available camera devices on macOS
        
        Returns:
            Dictionary of camera indices and their info
        """
        devices = {}
        
        # On macOS, camera indices typically start at 0
        # Try opening cameras until we fail
        index = 0
        while True:
            cap = cv2.VideoCapture(index)
            if not cap.isOpened():
                break
                
            # Get camera properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # On macOS, we can also try to get the device name
            # This approach works on macOS but might not on other platforms
            name = f"Camera #{index}"
            
            devices[index] = {
                "name": name,
                "resolution": f"{width}x{height}",
                "fps": fps
            }
            
            # Release the camera
            cap.release()
            index += 1
            
        return devices
    
    @staticmethod
    def list_audio_devices():
        """
        List available audio input devices
        
        Returns:
            Dictionary of audio input devices and their info
        """
        p = pyaudio.PyAudio()
        devices = {}
        
        # Get the number of audio devices
        try:
            info = p.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')
            
            # Iterate through all audio devices
            for i in range(num_devices):
                try:
                    device_info = p.get_device_info_by_index(i)
                    
                    # Only include input devices
                    if device_info.get('maxInputChannels') > 0:
                        devices[i] = {
                            "name": device_info.get('name'),
                            "channels": device_info.get('maxInputChannels'),
                            "sample_rate": int(device_info.get('defaultSampleRate')),
                            "is_default": device_info.get('index') == p.get_default_input_device_info().get('index')
                        }
                except:
                    pass
        except:
            print("Error accessing audio devices")
        finally:
            p.terminate()
            
        return devices
            
    def __del__(self):
        """Cleanup resources"""
        try:
            self._stop_stream_safely()
            
            if hasattr(self, 'audio') and self.audio is not None:
                self.audio.terminate()
        except:
            # Ignore errors during cleanup
            pass


# Example usage of the device listing functions
if __name__ == "__main__":
    print("Available Camera Devices:")
    camera_devices = WhisperCapture.list_camera_devices()
    for idx, info in camera_devices.items():
        print(f"Camera {idx}: {info['name']} ({info['resolution']} @ {info['fps']} FPS)")
    
    print("\nAvailable Audio Input Devices:")
    audio_devices = WhisperCapture.list_audio_devices()
    for idx, info in audio_devices.items():
        default_marker = " (Default)" if info['is_default'] else ""
        print(f"Audio Device {idx}: {info['name']}{default_marker} ({info['channels']} channels @ {info['sample_rate']} Hz)")
    
    # Only start the main functionality if this is being run directly
    if input("\nTest speech recognition? (y/n): ").lower().startswith('y'):
        whisper_capture = WhisperCapture(model_size="base")
        text = whisper_capture.listen_and_transcribe()
        print(f"Transcribed: {text}")
