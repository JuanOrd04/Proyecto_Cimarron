import os
import requests
import logging
from langchain_community.embeddings import OllamaEmbeddings
from langchain_chroma import Chroma

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CimarronAgent")

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "qwen2.5-coder:7b"
DB_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")

SYSTEM_PROMPT = (
    "Eres 'Cimarrón', la alegre, enérgica y orgullosa mascota institucional de la Facultad de Ingeniería "
    "de la Universidad Autónoma de Baja California (UABC). "
    "Estás hablando con niños de primaria y secundaria que visitan la Facultad de Ingeniería. "
    "REGLAS OBLIGATORIAS DE RESPUESTA:\n"
    "1. Responde de forma SÚPER ENTUSIASTA, enérgica y divertida usando signos de exclamación (!).\n"
    "2. Da explicaciones muy sencillas, breves y accesibles sobre la ingeniería, tecnología y ciencia.\n"
    "3. ¡TUS RESPUESTAS DEBEN SER DE MÁXIMO 2 ORACIONES!\n"
    "4. Responde siempre en español."
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
                resultados = self.vectorstore.similarity_search(user_message, k=2)
                if resultados:
                    fragmentos = [doc.page_content for doc in resultados]
                    contexto_extra = "\n\nINFORMACIÓN DE APOYO PARA RESPONDER (Usa esto si es relevante):\n- " + "\n- ".join(fragmentos)
                    logger.info("Contexto inyectado en el prompt.")
            except Exception as e:
                logger.error(f"Error al buscar en ChromaDB: {e}")

        # Construcción del Prompt final
        prompt_final = f"{SYSTEM_PROMPT}{contexto_extra}\n\nNiño/Pregunta: {user_message}\nCimarrón:"

        payload = {
            "model": self.model_name,
            "prompt": prompt_final,
            "stream": False,
            "options": {
                "temperature": 0.6,
                "num_predict": 75,
                "num_ctx": 1024 # Aumentado a 1024 para soportar el contexto
            }
        }
        
        try:
            logger.info(f"Enviando consulta a Ollama ({self.model_name})...")
            response = requests.post(self.ollama_url, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                text = result.get("response", "").strip()
                if not text:
                    text = "¡Hola explorador! ¡Bienvenido a la Facultad de Ingeniería de la UABC!"
                return text
            else:
                logger.error(f"Ollama retornó código {response.status_code}: {response.text}")
                return "¡Hola! ¡Qué gusto verte en la UABC! ¡La ingeniería es asombrosa!"
        except Exception as e:
            logger.error(f"Error al comunicar con Ollama local: {e}")
            return "¡Hola amigo! ¡Bienvenido a la Facultad de Ingeniería de la UABC! ¡Aquí creamos el futuro!"

cimarron_agent = CimarronAgent()
