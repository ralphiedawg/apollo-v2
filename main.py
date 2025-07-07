from core.chat import chat_with_apollo
from intents.classifier import get_final_intent

from core.memory.ShortTermMemory import ShortTermMemory
from core.memory.LongTermMemory import LongTermMemory

from core.tts.apollo_tts import ApolloTTS
from core.stt.WhisperCapture import WhisperCapture
from core.auth.face_authenticator import FaceAuthenticator

import subprocess

def format_memory_context(memory_entries):
    if not memory_entries:
        return ""
    context = "Conversation history:\n"
    for entry in memory_entries:
        context += f"[{entry['timestamp']}] User: {entry['user']}\nApollo: {entry['response']}\n"
    context += "\n"
    return context

def main():
    enable_speech = input("Enable speech synthesis? (yes/no): ").strip().lower() == "yes"
    enable_voice_input = input("Enable voice input with Whisper? (yes/no): ").strip().lower() == "yes"
    
    # Initialize components needed for authentication
    whisper_capture = None
    
    if enable_voice_input:
        print("Initializing speech recognition...")
        try:
            pause_time = float(input("Seconds to wait during speech pauses (default 2.0): ") or "2.0")
        except ValueError:
            print("Invalid value, using default 2.0 seconds")
            pause_time = 2.0
            
        whisper_capture = WhisperCapture(model_size="base", pause_threshold=pause_time)
    
    # Face Recognition Authentication
    print("\n" + "="*50)
    print("🔐 Apollo Authentication Required")
    print("="*50)
    
    face_auth = FaceAuthenticator()
    
    if not face_auth.authenticate(enable_voice_input, whisper_capture):
        print("Authentication failed. Exiting Apollo.")
        return
    
    print("Authentication successful! Starting Apollo...")
    print("Apollo Interactive Chat (type 'exit' to quit or press Ctrl+C to exit)")
    model = "gemma3:4b"

    # Initialize remaining components
    apollotts = None
    
    if enable_speech:
        print("Initializing text-to-speech...")
        apollotts = ApolloTTS()
        
        # Connect the components for feedback prevention
        if enable_voice_input:
            apollotts.set_whisper_capture(whisper_capture)

    memory = ShortTermMemory(max_entries=15)
    long_term_memory = LongTermMemory("cache/long_term_memory.json")

    while True:
        if enable_voice_input:
            print("\nSay something (or type 'manual' to switch to keyboard input for this turn):")
            try:
                user_input = whisper_capture.listen_and_transcribe()
                if user_input is None or user_input.strip().lower() == "manual":
                    user_input = input("\nYou (typing): ")
                else:
                    print(f"You (voice): {user_input}")
            except KeyboardInterrupt:
                print("\nSwitching to manual input for this turn.")
                user_input = input("\nYou (typing): ")
        else:
            user_input = input("\nYou: ")
            
        if user_input.strip().lower() in ("exit", "quit"):
            print("Exiting chat.")
            break

        intent_result = get_final_intent(user_input)
        intent = intent_result.get("intent", "none")

        # Always get the memory context to include in the prompt
        memory_context = format_memory_context(memory.get_context())

        if intent == "none" or intent == "general_query":
            # No actionable intent, generate a natural response
            prompt = memory_context + "User: " + user_input
            response = chat_with_apollo(model, prompt, False)
            print(f"Apollo: {response}")
            if enable_speech:
                apollotts.speak(response)
            memory.remember(user_input, response)

        elif intent == "store_info":
            fact = user_input
            new_fact = long_term_memory.remember(fact, user_input)
            response = f"I've stored your information as a fact: \"{new_fact['fact']}\""
            print(f"Apollo: {response}")
            if enable_speech:
                apollotts.speak(response)

        elif intent == "retrieve_info":
            all_facts = long_term_memory.recall_all()
            prompt = f"{memory_context} This user's prompt seems to be pertaining to stored information. Answer the user's question based off of your stored info: {all_facts}. The user's input is: {user_input}"
            response = chat_with_apollo(model, prompt, False)
            print(f"Apollo: {response}")
            if enable_speech:
                apollotts.speak(response)
           
        else:
            out = subprocess.run(
                ["./go/apolloctl", intent],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            print(f"[Apollo executed intent: {intent}]")
            prompt = (
                memory_context +
                f" The user has asked the question {user_input}. Summarize the result of the command {intent} and return it to me. The output is: {out.stdout}"
            )
            result = chat_with_apollo(model, prompt, False)
            if enable_speech:
                print(f"Apollo: {result}")
                apollotts.speak(result)
            memory.remember(user_input, result)

if __name__ == "__main__":
    main()
