from fastapi import FastAPI, UploadFile, File, Response, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from core.chat import chat_with_apollo
from intents.classifier import get_final_intent
from core.memory.ShortTermMemory import ShortTermMemory
from core.memory.LongTermMemory import LongTermMemory
from core.tts.apollo_tts import ApolloTTS
import subprocess
import tempfile
import os
from typing import Optional, List
from itertools import count

app = FastAPI()

# Enable CORS for all origins (for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    user_input: str
    chat_id: int

class CreateChatResponse(BaseModel):
    chat_id: int
    name: str

class ChatIDInfo(BaseModel):
    chat_id: int
    name: str

class RenameChatRequest(BaseModel):
    chat_id: int
    name: str

class DeleteChatRequest(BaseModel):
    chat_id: int

class TTSRequest(BaseModel):
    text: str
    volume: float = 1.0

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

apollotts = ApolloTTS()
long_term_memory = LongTermMemory("cache/long_term_memory.json")
model = "gemma3:4b"

# Each conversation is a dict: {"memory": ShortTermMemory, "name": str, "history": list}
chat_memories = {}
chat_id_counter = count(1)

DEFAULT_CONVO_NAME = "New Conversation"

def format_memory_context(memory_entries):
    if not memory_entries:
        return ""
    context = "Conversation history:\n"
    for entry in memory_entries:
        context += f"[{entry['timestamp']}] User: {entry['user']}\nApollo: {entry['response']}\n"
    context += "\n"
    return context

@app.post("/create_chat", response_model=CreateChatResponse)
async def create_chat():
    chat_id = next(chat_id_counter)
    chat_memories[chat_id] = {
        "memory": ShortTermMemory(max_entries=15),
        "name": DEFAULT_CONVO_NAME,
        "history": []
    }
    return {"chat_id": chat_id, "name": DEFAULT_CONVO_NAME}

@app.post("/rename_chat")
async def rename_chat(req: RenameChatRequest):
    chat = chat_memories.get(req.chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat ID not found.")
    chat["name"] = req.name
    return {"chat_id": req.chat_id, "name": req.name}

@app.post("/delete_chat")
async def delete_chat(req: DeleteChatRequest):
    if req.chat_id in chat_memories:
        del chat_memories[req.chat_id]
        return {"success": True}
    else:
        raise HTTPException(status_code=404, detail="Chat ID not found.")

@app.get("/chat_history")
async def get_chat_history(chat_id: int = Query(...)):
    chat = chat_memories.get(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat ID not found.")
    return chat["history"]

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    chat_id = req.chat_id
    user_input = req.user_input

    chat = chat_memories.get(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat ID not found. Create a new chat with /create_chat.")
    memory = chat["memory"]
    history = chat.setdefault("history", [])

    # Add user message to history
    history.append({"role": "user", "content": user_input})

    intent_result = get_final_intent(user_input)
    intent = intent_result.get("intent", "none")
    memory_context = format_memory_context(memory.get_context())

    def stream_response():
        if intent == "none" or intent == "general_query":
            prompt = memory_context + "User: " + user_input
            response_text = ""
            try:
                for chunk in chat_with_apollo(model, prompt, stream=True):
                    response_text += chunk
                    yield chunk
                memory.remember(user_input, response_text)
                # Add assistant message to history
                history.append({"role": "assistant", "content": response_text})
            except Exception as e:
                yield f"\n[Error: {str(e)}]\n"
                history.append({"role": "assistant", "content": f"[Error: {str(e)}]"})
        elif intent == "store_info":
            fact = user_input
            new_fact = long_term_memory.remember(fact, user_input)
            response = f"I've stored your information as a fact: \"{new_fact['fact']}\""
            memory.remember(user_input, response)
            history.append({"role": "assistant", "content": response})
            yield response
        elif intent == "retrieve_info":
            all_facts = long_term_memory.recall_all()
            prompt = f"{memory_context} This user's prompt seems to be pertaining to stored information. Answer the user's question based off of your stored info: {all_facts}. The user's input is: {user_input}"
            response_text = ""
            try:
                for chunk in chat_with_apollo(model, prompt, stream=True):
                    response_text += chunk
                    yield chunk
                memory.remember(user_input, response_text)
                history.append({"role": "assistant", "content": response_text})
            except Exception as e:
                yield f"\n[Error: {str(e)}]\n"
                history.append({"role": "assistant", "content": f"[Error: {str(e)}]"})
        else:
            if not os.path.isfile("./go/apolloctl"):
                error_msg = "[Error: apolloctl binary not found.]"
                yield error_msg
                history.append({"role": "assistant", "content": error_msg})
                return
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
                response_text = ""
                for chunk in chat_with_apollo(model, prompt, stream=True):
                    response_text += chunk
                    yield chunk
                memory.remember(user_input, response_text)
                history.append({"role": "assistant", "content": response_text})
            except subprocess.CalledProcessError as e:
                error_msg = f"[Go command failed: {e.stderr}]"
                yield error_msg
                history.append({"role": "assistant", "content": error_msg})

    return StreamingResponse(stream_response(), media_type="text/plain")

@app.get("/list_chats", response_model=List[ChatIDInfo])
async def list_chats():
    """
    Return a list of all active chat IDs and their names.
    """
    return [
        ChatIDInfo(chat_id=cid, name=chat["name"])
        for cid, chat in chat_memories.items()
    ]

@app.post("/tts")
async def tts_endpoint(req: TTSRequest, background_tasks: BackgroundTasks):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
        wav_path = tmpfile.name
    apollotts.speak_to_file(req.text, wav_path)
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
