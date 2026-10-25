import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import uvicorn
import logging
from contextlib import asynccontextmanager

from cimarron_agent import cimarron_agent
from ollama_client import OLLAMA_BASE_URL, MODEL_NAME
from tts_engine import tts_service
from quiz_api import router as quiz_router
from quiz_engine import quiz_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MainFastAPI")


@asynccontextmanager
async def lifespan(app):
    quiz_service.generator.warm_audio()
    yield
    quiz_service.generator.close()


app = FastAPI(
    title="Asistente Interactivo Cimarrón UABC - API Backend",
    description="Servidor local para conversar con Ollama, evaluar respuestas de primaria por significado y generar voz con Supertonic.",
    version="1.0.0",
    lifespan=lifespan,
)

# Permitir CORS desde el frontend local (Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Habilitado para desarrollo local en http://localhost:5173 / 127.0.0.1:5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(quiz_router)

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
    quiz_model_available = False
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        if r.status_code == 200:
            ollama_online = True
            models = {model['name'] for model in r.json().get('models', [])}
            quiz_model_available = quiz_service.evaluator.model in models
    except Exception:
        ollama_online = False

    return {
        "status": "online",
        "backend": "FastAPI 100% Local",
        "ollama_status": "conectado" if ollama_online else "desconectado (asegúrate de correr 'ollama serve')",
        "llm_model": MODEL_NAME,
        "quiz_model": quiz_service.evaluator.model,
        "quiz_model_status": "instalado" if quiz_model_available else "no disponible",
    }

class TeachRequest(BaseModel):
    text: str

@app.post("/teach")
def teach_endpoint(request: TeachRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="El texto no puede estar vacío.")
    
    success = cimarron_agent.add_knowledge(request.text)
    if success:
        return {"status": "ok", "message": "Base de datos actualizada en tiempo real."}
    else:
        raise HTTPException(status_code=500, detail="Error al actualizar la base de datos.")

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
