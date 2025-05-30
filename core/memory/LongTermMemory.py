import json

class LongTermMemory:
    def __init__(self, file_path):
        self.file_path = file_path
        with open(self.file_path, 'r') as file:
            self.data = json.load(file)
        
    def recall(self, keyword):
        for fact in self.data["facts"]:
            if keyword.lower() in fact["fact"].lower():
                return fact["fact"]
        return "No relevant fact found."

    def recall_from_uuid(self, uuid):
        for fact in self.data["facts"]:
            if fact["uuid"] == uuid:
                return fact["fact"]
        return "No fact found with the given UUID."

    def recall_all(self):
        return [fact["fact"] for fact in self.data["facts"]]

    def get_next_id(self):
        if not self.data["facts"]:
            return 1
        return max(int(fact["id"]) for fact in self.data["facts"]) + 1  

    def remember(self, fact, raw_input):
        new_fact = {
            "id": self.get_next_id(),
            "fact": fact,
            "raw_input": raw_input
        }
        self.data["facts"].append(new_fact)
        with open(self.file_path, 'w') as file:
            json.dump(self.data, file, indent=4)
        return new_fact

if __name__ == "__main__":
    ltm = LongTermMemory("cache/long_term_memory.json")
    print(ltm.recall("purple"))
