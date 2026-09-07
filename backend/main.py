import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import uvicorn
import logging

from cimarron_agent import cimarron_agent, OLLAMA_URL
from tts_engine import tts_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MainFastAPI")

app = FastAPI(
    title="Asistente Interactivo Cimarrón UABC - API Backend",
    description="Servidor local FastAPI para inferencia LLM (Ollama qwen2.5-coder:7b) y TTS local en formato WAV Base64.",
    version="1.0.0"
)

# Permitir CORS desde el frontend local (Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Habilitado para desarrollo local en http://localhost:5173 / 127.0.0.1:5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    audio: str  # Audio Data URI en Base64 (data:audio/wav;base64,...)

CACHE_FILE = "qa_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache_data):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False)

qa_cache = load_cache()

@app.get("/health")
def health_check():
    """Verifica el estado del backend y la disponibilidad del servidor local Ollama."""
    ollama_online = False
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
        if r.status_code == 200:
            ollama_online = True
    except Exception:
        ollama_online = False

    return {
        "status": "online",
        "backend": "FastAPI 100% Local",
        "ollama_status": "conectado" if ollama_online else "desconectado (asegúrate de correr 'ollama serve')"
    }

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    Endpoint principal para interacción con el Cimarrón.
    1. Recibe el texto del usuario.
    2. Si el texto está en caché, retorna al instante (0 ms).
    3. Si no, genera respuesta con Ollama y la voz con Supertonic.
    """
    user_msg = request.message.strip() if request.message else ""
    if not user_msg:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    # 1. VERIFICAR CACHÉ
    if user_msg in qa_cache:
        logger.info(f"⚡ [CACHÉ HIT] Retornando respuesta guardada para: '{user_msg}'")
        cached_data = qa_cache[user_msg]
        return ChatResponse(
            response=cached_data["response"],
            audio=cached_data["audio"]
        )

    logger.info(f"🤖 [NUEVA PREGUNTA] '{user_msg}'")
    
    # 2. Inferencia LLM
    cimarron_text = cimarron_agent.generate_response(user_msg)
    logger.info(f"Respuesta generada por Cimarrón: '{cimarron_text}'")
    
    # 3. Síntesis TTS a Base64 WAV
    audio_base64 = tts_service.synthesize_to_base64_wav(cimarron_text)
    
    # 4. Guardar en caché
    qa_cache[user_msg] = {
        "response": cimarron_text,
        "audio": audio_base64
    }
    save_cache(qa_cache)

    return ChatResponse(
        response=cimarron_text,
        audio=audio_base64
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
