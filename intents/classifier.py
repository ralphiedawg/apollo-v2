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
    You are an intent classifier for Apollo, a voice assistant. 
    Analyze the user's message and determine if it contains an actionable intent.
    
    Return no explanation of decisions nor markdown.
    Finally, Return exactly the name of the intent you are given. Do not change it whatsoever.
    Return nothing but a JSON object with the following structure, no wrapping text or anything:
    {
        "intent": "snake_case_intent_name",
        "requires_confirmation": true/false
    }
    the requires_confirmation should be a boolean based off of the requires_confirmation field inside list of intents you are given.
    If unsure, set requires_confirmation to be 'false' if it's a non-destructive action.
    
    If no intent is detected, set "intent" to "none".
    Always use lowercase snake_case for the intent name.
    
    User Input = "Are my systems online?"
    Available intents:
    """
    classifier_prompt += intents;
    classifier_response = chat_with_apollo("llama3.2:1b", classifier_prompt, True)
    print(classifier_response)


if __name__ == "__main__":
    classify_intent(get_intents("intents/intents.yaml"))
