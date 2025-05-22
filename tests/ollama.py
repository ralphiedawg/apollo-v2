import requests
import json
import os

def get_ollama_status():
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout = 2)
        if response.status_code == 200:
            return "Ollama System Online"
        else: 
            return f"Error occured while connecting to Ollama: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return f"Ollama is not responding: {str(e)}"
