import yaml
#from ..core.chat import chat_with_apollo

def get_intents(document_path):
    available_intents = []

    with open(document_path, 'r') as file:
        try:
            data = yaml.safe_load(file)
            for intent_name, intent_data in data.items():
                description = intent_data.get("description", "No description provided")
                available_intents.append(f"{intent_name}: {description}")
        except yaml.YAMLError as err:
            print(f"YAML error: {err}")
            exit()

    returned = ""
    for intent in available_intents:
        returned += intent
    print(returned)
    return returned;

def classify_intent(intents):
    pass

if __name__ == "__main__":
    get_intents("intents/intents.yaml")
