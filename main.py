from core.chat import chat_with_apollo
from intents.classifier import get_final_intent
import subprocess

def main():
    print("Apollo Interactive Chat (type 'exit' to quit)")
    model = "llama3.2"  # or whatever your default is

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
        else:
            # Intent found: execute intent (stub, implement as needed)
            print(f"[Apollo executed intent: {intent}]")
            subprocess.run(["./go/apolloctl", intent])


if __name__ == "__main__":
    main()
