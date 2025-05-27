import json
from datetime import datetime

def save_to_memory(memory_file, user, response):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "user": user,
        "response": response
    }
    try:
        with open(memory_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception as e:
        print(f"Error saving to memory: {e}")

def get_memory(memory_file):
    entries = []
    try:
        with open(memory_file, 'r') as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
    except Exception as e:
        print(f"Error reading memory: {e}")
    return entries
