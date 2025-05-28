from core.chat import chat_with_apollo
from core.tts.apollo_tts import *
from intents.classifier import get_final_intent
from core.memory.memory_utils import save_to_memory

import subprocess

def main():
    print("Apollo Interactive Chat (type 'exit' to quit)")
    model = "llama3.2"  # or whatever your default is
    
    apollotts = ApolloTTS() # Check out core/tts/apollo_tts to modify or see how to change tts behavior 

    while True:
        user_input = input("\nYou: ")
        if user_input.strip().lower() in ("exit", "quit"):
            print("Exiting chat.")
            break

        intent_result = get_final_intent(user_input)
        intent = intent_result.get("intent", "none")

        if intent == "none":
            # No actionable intent, generate a natural response
            response = chat_with_apollo(model, user_input, False)
            print(f"Apollo: {response}")
            apollotts.speak(response)
            save_to_memory("cache/memory.json", user_input, response)
        else:
            out = subprocess.run(
                ["./go/apolloctl", intent],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
            )
            print(f"[Apollo executed intent: {intent}]")
            result = chat_with_apollo(model, f" The user has asked the question {user_input}. Summarize the result of the command {intent} and return it to me. The output is: {out.stdout}", False)
            apollotts.speak(result)
            save_to_memory("cache/memory.json", user_input, result)


if __name__ == "__main__":
    main()
