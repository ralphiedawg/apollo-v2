import yaml
import json
from core.chat import chat_with_apollo

def get_intents(document_path):
    intents = []

    with open(document_path, 'r') as file:
        try:
            data = yaml.safe_load(file)
            for intent_name, intent_data in data.items():
                description = intent_data.get("description", "No description provided")
                requires_confirmation = intent_data.get("requires_confirmation", False)
                intents.append(f"{intent_name}: {description}\nrequires_confirmation: {requires_confirmation}\n")
        except yaml.YAMLError as err:
            print(f"YAML error: {err}")
            exit()

    return "\n".join(intents)

def classify_intent(intents, prompt):
    classifier_prompt = """
    You are an intent classifier for Apollo, a voice assistant.  
    Your job is to analyze the user's message and select the single most appropriate intent from the provided list.

    Rules:
    - Only choose one of the valid intents listed below.
    - If none apply, return exactly:
    {
      "intent": "none"
    }
    - Otherwise, return exactly:
    {
      "intent": "{selected_intent_in_lower_snake_case}"
    }
    - Do NOT invent new intent names, even if the user's input is unrelated.
    - Always use lowercase snake_case for intent names.
    - Never add markdown, extra text, or explanations—just the raw JSON as shown.
    - If the intent requires confirmation, you can return it without confirmation.
    - Greetings, small talk, and other casual interactions are not intents nor things to remember and should return "none".

    Available intents (only these are valid):
    """

    classifier_prompt += intents
    classifier_prompt += "\n\nThe user's prompt is:\n"
    classifier_prompt += prompt
    
    return chat_with_apollo("llama3.2", classifier_prompt, True)

def parse_llm_response(response):
    try: 
        data = json.loads(response)
        return data.get("intent", "none")
    except json.JSONDecodeError as err:
        print(f"Error occurred while decoding JSON: {err}")
        print("Raw response:", response)
        return "none"

def get_final_intent(message):
    intents = get_intents("intents/intents.yaml")
    response = classify_intent(intents, message)
    intent = parse_llm_response(response)
    return {"intent": intent}

if __name__ == "__main__":
    proompt = input("> ")
    result = get_final_intent(proompt)
    print(f"\nSELECTED INTENT: {result['intent']}")
