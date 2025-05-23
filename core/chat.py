import requests
import json

def chat_with_apollo():
    returned = ""
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3.2:1b", "prompt": "Say apple, quick!", "stream": False}
    )
    try:
        lines = response.text.strip().splitlines()
        for line in lines:
            data = json.loads(line)
            returned += data["response"]
    except Exception as e:
        returned += f"Failed to parse response: {e}" 
        returned += "Raw response:"
        returned += response.text

