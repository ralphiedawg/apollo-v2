import os
import tempfile
import json
import uuid
from typing import Dict, List, Optional, Any
import base64
import threading

from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.chat import chat_with_apollo
from core.memory.ShortTermMemory import ShortTermMemory
from core.tts.apollo_tts import ApolloTTS
from core.stt.WhisperCapture import WhisperCapture
from intents.classifier import get_final_intent

# Initialize TTS
apollotts = ApolloTTS()

# Initialize WhisperCapture for STT
whisper_model = WhisperCapture(model_size="base", pause_threshold=2.0)

# Connect TTS and STT for coordination
apollotts.set_whisper_capture(whisper_model)

# Create FastAPI app
app = FastAPI(title="Apollo V2 API", 
              description="HTTP API for Apollo V2 personal assistant",
              version="0.1.0")

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chat memory storage (in-memory for now)
chat_memories = {}

# Models for request/response
class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None
    model: str = "gemma3:4b"
    name: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    chat_id: str

class ChatIDInfo(BaseModel):
    chat_id: str
    name: str

class TTSRequest(BaseModel):
    text: str
    
class STTRequest(BaseModel):
    audio_base64: str  # Base64 encoded audio data

# Get or create memory for chat
def get_chat_memory(chat_id: str, name: Optional[str] = None) -> Dict:
    if chat_id not in chat_memories:
        chat_memories[chat_id] = {
            "memory": ShortTermMemory(max_entries=15),
            "name": name if name else f"Chat {chat_id[:8]}"
        }
    elif name and not chat_memories[chat_id]["name"].startswith("Chat "):
        # Update name if provided and not already set
        chat_memories[chat_id]["name"] = name
    return chat_memories[chat_id]

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """
    Main chat endpoint - send a message and get a response.
    Optionally provide a chat_id to continue a conversation.
    """
    # Generate a new chat ID if one wasn't provided
    chat_id = req.chat_id if req.chat_id else str(uuid.uuid4())
    
    # Get or create memory for this chat
    chat_data = get_chat_memory(chat_id, req.name)
    memory = chat_data["memory"]
    
    # Get memory context
    memory_context = ""
    context_entries = memory.get_context()
    if context_entries:
        memory_context = "Conversation history:\n"
        for entry in context_entries:
            memory_context += f"[{entry['timestamp']}] User: {entry['user']}\nApollo: {entry['response']}\n"
        memory_context += "\n"
    
    # Process the message with intent classification
    intent_result = get_final_intent(req.message)
    intent = intent_result.get("intent", "none")
    
    # Handle the message based on intent
    if intent in ["none", "general_query"]:
        # Standard conversation
        prompt = memory_context + "User: " + req.message
        response = chat_with_apollo(req.model, prompt, False)
    else:
        # Handle other intents here in the future
        response = f"Intent '{intent}' detected but not implemented in API yet."
    
    # Remember this interaction
    memory.remember(req.message, response)
    
    return ChatResponse(message=response, chat_id=chat_id)

@app.get("/chat/{chat_id}", response_model=List[Dict[str, Any]])
async def get_chat_history(chat_id: str):
    """
    Get the chat history for a specific chat ID.
    """
    if chat_id not in chat_memories:
        raise HTTPException(status_code=404, detail="Chat not found")
        
    memory = chat_memories[chat_id]["memory"]
    return memory.get_all()

@app.delete("/chat/{chat_id}")
async def delete_chat(chat_id: str):
    """
    Delete a chat and its memory.
    """
    if chat_id in chat_memories:
        del chat_memories[chat_id]
        return {"status": "deleted"}
    else:
        raise HTTPException(status_code=404, detail="Chat not found")

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
    """
    Convert text to speech and return WAV audio file
    """
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

@app.post("/stt")
async def stt_endpoint(req: STTRequest, background_tasks: BackgroundTasks):
    """
    Convert speech to text using Whisper
    Accepts base64 encoded audio data
    """
    try:
        # Decode base64 audio data
        audio_data = base64.b64decode(req.audio_base64)
        
        # Save to temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
            wav_path = tmpfile.name
            tmpfile.write(audio_data)
        
        # Create a recognizer and convert the file
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
        
        # Perform transcription
        transcription = whisper_model.recognize_speech(audio)
        
        # Clean up
        background_tasks.add_task(os.remove, wav_path)
        
        return {"text": transcription}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")

@app.post("/upload_audio")
async def upload_audio(file: UploadFile = File(...)):
    """
    Upload an audio file for transcription
    """
    try:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
            wav_path = tmpfile.name
            content = await file.read()
            tmpfile.write(content)
        
        # Create a recognizer and convert the file
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
        
        # Perform transcription
        transcription = whisper_model.recognize_speech(audio)
        
        # Clean up
        os.remove(wav_path)
        
        return {"text": transcription}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")

@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {"message": "Apollo V2 HTTP API is running."}

# Serve static files if available
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount web UI if available
webui_dir = os.path.join(os.path.dirname(__file__), "..", "webui", "build")
if os.path.exists(webui_dir):
    app.mount("/", StaticFiles(directory=webui_dir, html=True), name="webui")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
