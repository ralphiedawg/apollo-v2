from core.chat import chat_with_apollo
from core.tts.apollo_tts import *
from intents.classifier import get_final_intent
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

        # Step 1: Classify intent
        intent_result = get_final_intent(user_input)
        intent = intent_result.get("intent", "none")

        # Step 2: Branch based on intent
        if intent == "none":
            # No actionable intent, generate a natural response
            response = chat_with_apollo(model, user_input, False)
            print(f"Apollo: {response}")
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
            #apollotts.speak(f"Intent {intent} executed.")
            result = chat_with_apollo(model, f" Summarize the result of the command {intent} and return it to me. The output is: {out.stdout}", False)
            apollotts.speak(result)


if __name__ == "__main__":
    main()
