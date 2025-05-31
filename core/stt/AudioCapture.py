import speech_recognition as sr

class AudioCapture:
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def capture_audio(self):
        with sr.Microphone() as source:
            print("Say something!")
            audio = self.recognizer.listen(source)
        return audio

    def recognize_speech(self, audio):
        try:
            text = self.recognizer.recognize_google(audio)
            print("You said:", text)
            return text
        except sr.UnknownValueError:
            print("Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            return None


if __name__ == "__main__":
    audio_capture = AudioCapture()
    audio = audio_capture.capture_audio()
    audio_capture.recognize_speech(audio)
