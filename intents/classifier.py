import yaml
from core.chat import chat_with_apollo

def get_intents(document_path):
    available_intents = []

    with open(document_path, 'r') as file:
        try:
            data = yaml.safe_load(file)
            for intent_name, intent_data in data.items():
                description = intent_data.get("description", "No description provided")
                requires_confirmation = intent_data.get("requires_confirmation", False)
                available_intents.append(f"{intent_name}: {description} \nrequires_confirmation: {requires_confirmation}\n")
        except yaml.YAMLError as err:
            print(f"YAML error: {err}")
            exit()

    returned = ""
    for intent in available_intents:
        returned += intent
    return returned;

def classify_intent(intents):
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
    classifier_prompt += intents;
    classifier_prompt += "The User's prompt is:"
    classifier_prompt += input("> ")
    classifier_response = chat_with_apollo("llama3.2", classifier_prompt, True)
    print(classifier_response)


if __name__ == "__main__":
    classify_intent(get_intents("intents/intents.yaml"))
