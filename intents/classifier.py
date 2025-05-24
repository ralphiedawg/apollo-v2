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
    You are a part of an intent classifier system for Apollo, a voice assistant. 
    Your only purpose to exist is to analyze the user's message and determine if it matches or contains an actionable intent from the list of actionable intents you're provided. 
        
    Only choose one of the listed intents. If none of them apply, return:

    {
      "intent": "none",
    }

    Otherwise, return 
    {
      "intent": "{selected_intent_in_lower_snake_case_here",
    }

    Do not invent any new intent names, even if the input appears unrelated.

    If an intent requires confirmation, the confirmation template for you to follow will be supplied, so it's safe to assume it's not needed. 
    
    If no intent matching an item in the given list is detected, set "intent" to "none".
    Always use lowercase snake_case for the intent name.
    Finally, remember you are always able to answer none if the user's prompt doesn't match any of the listed intents.
    
    Available intents (Only these are valid):
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
