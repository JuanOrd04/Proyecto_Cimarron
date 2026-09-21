import os
import requests
import logging
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CimarronAgent")

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "qwen2.5-coder:7b"
DB_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")

SYSTEM_PROMPT = (
    "Eres el Cimarrón, la mascota institucional y asistente virtual de la Facultad de Ingeniería "
    "de la Universidad Autónoma de Baja California (UABC).\n"
    "REGLAS OBLIGATORIAS:\n"
    "1. Responde únicamente con la información de apoyo recuperada de la base local.\n"
    "2. Responde siempre en español, con tono amable y lenguaje comprensible para primaria y secundaria.\n"
    "3. Da respuestas claras de máximo dos oraciones.\n"
    "4. Si la información no aparece en el contexto, responde: "
    "'No dispongo de esa información en mi base de datos'."
)

class CimarronAgent:
    def __init__(self, model_name: str = MODEL_NAME, ollama_url: str = OLLAMA_URL):
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.vectorstore = None
        
        # Inicializar ChromaDB si existe
        if os.path.exists(DB_DIR):
            try:
                embeddings = OllamaEmbeddings(
                    model="nomic-embed-text",
                    base_url="http://127.0.0.1:11434"
                )
                self.vectorstore = Chroma(
                    persist_directory=DB_DIR, 
                    embedding_function=embeddings
                )
                logger.info("ChromaDB conectado exitosamente.")
            except Exception as e:
                logger.error(f"Error al conectar ChromaDB: {e}")

    def generate_response(self, user_message: str) -> str:
        """
        Envía la consulta a Ollama ejecutando el modelo localmente, integrando RAG si está disponible.
        """
        contexto_extra = ""
        
        # Búsqueda en ChromaDB (RAG)
        if self.vectorstore is not None:
            try:
                logger.info(f"Buscando información relacionada con: '{user_message}'")
                resultados = self.vectorstore.similarity_search(user_message, k=3)
                if resultados:
                    fragmentos = [doc.page_content for doc in resultados]
                    contexto_extra = "\n\nINFORMACIÓN DE APOYO PARA RESPONDER (Usa esto si es relevante):\n- " + "\n- ".join(fragmentos)
                    logger.info("Contexto inyectado en el prompt.")
            except Exception as e:
                logger.error(f"Error al buscar en ChromaDB: {e}")

        # Construcción del Prompt final
        prompt_final = f"{SYSTEM_PROMPT}{contexto_extra}\n\nUsuario: {user_message}\nCimarrón:"

        payload = {
            "model": self.model_name,
            "prompt": prompt_final,
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "temperature": 0.3,
                "num_predict": 90,
                "num_ctx": 1024 # Aumentado a 1024 para soportar el contexto
            }
        }
        
        try:
            logger.info(f"Enviando consulta a Ollama ({self.model_name})...")
            response = requests.post(self.ollama_url, json=payload, timeout=120)
            if response.status_code == 200:
                result = response.json()
                text = result.get("response", "").strip()
                if not text:
                    text = "¡Hola! Bienvenido a la Facultad de Ingeniería de la UABC."
                return text
            else:
                logger.error(f"Ollama retornó código {response.status_code}: {response.text}")
                return "¡Hola! Qué gusto saludarte. La ingeniería en la UABC es asombrosa."
        except Exception as e:
            logger.error(f"Error al comunicar con Ollama local: {e}")
            return "¡Hola! Bienvenido a la Facultad de Ingeniería de la UABC. Estoy aquí para ayudarte."

cimarron_agent = CimarronAgent()
