import requests
import json
from core.preprompt.get_preprompt import preprompt as get_preprompt

def chat_with_apollo(model, prompt, stream=False):
    preprompt = get_preprompt("core/preprompt/values.yaml")
    full_prompt = "System Prompt: \n" + preprompt + "\n\nUser: " + prompt + "\nApollo:"

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": full_prompt, "stream": stream}
    )

    output = ""

    try:
        if stream:
            for line in response.iter_lines(decode_unicode=True):
                if line.strip():
                    data = json.loads(line)
                    output += data.get("response", "")
        else:
            data = response.json()
            output = data.get("response", "")
    except Exception as e:
        output = f"Failed to parse response: {e}\nRaw response:\n{response.text}"

    return output
