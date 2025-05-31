from core.chat import chat_with_apollo
from intents.classifier import get_final_intent

from core.memory.ShortTermMemory import ShortTermMemory
from core.memory.LongTermMemory import LongTermMemory

from core.tts.apollo_tts import *
from core.stt.AudioCapture import AudioCapture


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
    print("Apollo Interactive Chat (type 'exit' to quit)")
    model = "gemma3:4b"

    apollotts = ApolloTTS()
    memory = ShortTermMemory(max_entries=15)
    long_term_memory = LongTermMemory("cache/long_term_memory.json")

    while True:
        user_input = input("\nYou: ")
        if user_input.strip().lower() in ("exit", "quit"):
            print("Exiting chat.")
            break

        intent_result = get_final_intent(user_input)
        intent = intent_result.get("intent", "none")

        # Always get the memory context to include in the prompt
        memory_context = format_memory_context(memory.get_context())

        if intent == "none":
            # No actionable intent, generate a natural response
            prompt = memory_context + "User: " + user_input
            response = chat_with_apollo(model, prompt, False)
            print(f"Apollo: {response}")
            apollotts.speak(response)
            memory.remember(user_input, response)

        elif intent == "store_info":
            fact = user_input
            new_fact = long_term_memory.remember(fact, user_input)
            response = f"I've stored your information as a fact: \"{new_fact['fact']}\""
            print(f"Apollo: {response}")
            apollotts.speak(response)

        elif intent == "retrieve_info":
            all_facts = long_term_memory.recall_all()
            prompt = f"{memory_context} This user's prompt seems to be pertaining to stored information. Answer the user's question based off of your stored info: {all_facts}. The user's input is: {user_input}"
            response = chat_with_apollo(model, prompt, False)
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
            prompt = (
                memory_context +
                f" The user has asked the question {user_input}. Summarize the result of the command {intent} and return it to me. The output is: {out.stdout}"
            )
            result = chat_with_apollo(model, prompt, False)
            apollotts.speak(result)
            memory.remember(user_input, result)

if __name__ == "__main__":
    main()
