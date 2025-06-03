from fastapi import FastAPI, UploadFile, File, Response, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from core.chat import chat_with_apollo
from intents.classifier import get_final_intent
from core.memory.ShortTermMemory import ShortTermMemory
from core.memory.LongTermMemory import LongTermMemory
from core.tts.apollo_tts import ApolloTTS
import subprocess
import tempfile
import os

app = FastAPI()

class ChatRequest(BaseModel):
    user_input: str

class TTSRequest(BaseModel):
    text: str
    volume: float = 1.0

apollotts = ApolloTTS()
memory = ShortTermMemory(max_entries=15)
long_term_memory = LongTermMemory("cache/long_term_memory.json")
model = "gemma3:4b"

def format_memory_context(memory_entries):
    if not memory_entries:
        return ""
    context = "Conversation history:\n"
    for entry in memory_entries:
        context += f"[{entry['timestamp']}] User: {entry['user']}\nApollo: {entry['response']}\n"
    context += "\n"
    return context

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    user_input = req.user_input
    intent_result = get_final_intent(user_input)
    intent = intent_result.get("intent", "none")
    memory_context = format_memory_context(memory.get_context())

    if intent == "none":
        prompt = memory_context + "User: " + user_input
        response = chat_with_apollo(model, prompt, False)
        memory.remember(user_input, response)
        return {"response": response, "intent": intent}

    elif intent == "store_info":
        fact = user_input
        new_fact = long_term_memory.remember(fact, user_input)
        response = f"I've stored your information as a fact: \"{new_fact['fact']}\""
        return {"response": response, "intent": intent}

    elif intent == "retrieve_info":
        all_facts = long_term_memory.recall_all()
        prompt = f"{memory_context} This user's prompt seems to be pertaining to stored information. Answer the user's question based off of your stored info: {all_facts}. The user's input is: {user_input}"
        response = chat_with_apollo(model, prompt, False)
        return {"response": response, "intent": intent}

    else:
        # Go intent execution
        try:
            out = subprocess.run(
                ["./go/apolloctl", intent],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            prompt = (
                memory_context +
                f" The user has asked the question {user_input}. Summarize the result of the command {intent} and return it to me. The output is: {out.stdout}"
            )
            result = chat_with_apollo(model, prompt, False)
            memory.remember(user_input, result)
            return {
                "response": result,
                "go_stdout": out.stdout,
                "intent": intent
            }
        except subprocess.CalledProcessError as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": f"Go command failed: {e.stderr}",
                    "intent": intent,
                    "returncode": e.returncode
                }
            )

@app.post("/tts")
async def tts_endpoint(req: TTSRequest, background_tasks: BackgroundTasks):
    # Synthesize speech and stream the wav file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
        wav_path = tmpfile.name
    apollotts.speak_to_file(req.text, wav_path)  # Add volume param here if supported
    filename = "output.wav"
    background_tasks.add_task(os.remove, wav_path)
    return FileResponse(
        wav_path,
        media_type="audio/wav",
        filename=filename
    )

@app.get("/")
async def root():
    return {"message": "Apollo V2 HTTP API is running."}
