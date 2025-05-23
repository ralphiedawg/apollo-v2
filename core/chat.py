import requests
import json

def chat_with_apollo(model, prompt, stream):
    returned = ""
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": stream}
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

