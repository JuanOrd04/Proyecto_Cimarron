import os
import requests
import logging
from langchain_community.embeddings import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CimarronAgent")

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "gemma2:2b"
DB_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")

SYSTEM_PROMPT = (
    "Eres el 'Cimarrón', la orgullosa mascota institucional y asistente virtual de la Facultad de Ingeniería "
    "de la Universidad Autónoma de Baja California (UABC). "
    "REGLAS OBLIGATORIAS DE RESPUESTA:\n"
    "1. Responde con un tono neutro, amable y accesible para todo el público (tanto adultos como niños).\n"
    "2. Da explicaciones claras, breves y precisas sobre la ingeniería y la facultad.\n"
    "3. TUS RESPUESTAS DEBEN SER DE MÁXIMO 2 ORACIONES.\n"
    "4. Responde siempre en español.\n"
    "5. MUY IMPORTANTE: Para temas académicos, carreras o datos específicos, SOLO responde con la INFORMACIÓN DE APOYO. Si te preguntan algo que NO está ahí, responde: 'No tengo esa información, pero te invito a preguntar sobre nuestras carreras o instalaciones'. NUNCA inventes datos. Puedes responder normalmente a saludos ('hola', 'cómo estás')."
)

class CimarronAgent:
    def __init__(self, model_name: str = MODEL_NAME, ollama_url: str = OLLAMA_URL):
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.vectorstore = None
        self.history = []
        
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
                query_to_search = user_message
                for msg in reversed(self.history):
                    if msg.startswith("Usuario:"):
                        query_to_search = msg.replace("Usuario: ", "").strip() + " " + user_message
                        break
                logger.info(f"Buscando en BD Vectorial: '{query_to_search}'")
                resultados = self.vectorstore.similarity_search(query_to_search, k=4)
                if resultados:
                    fragmentos = [doc.page_content for doc in resultados]
                    contexto_extra = "\n\nINFORMACIÓN DE APOYO PARA RESPONDER (Usa esto si es relevante):\n- " + "\n- ".join(fragmentos)
                    logger.info("Contexto inyectado en el prompt.")
            except Exception as e:
                logger.error(f"Error al buscar en ChromaDB: {e}")

        # Construcción del Prompt final
        self.history.append(f"Usuario: {user_message}")
        if len(self.history) > 4:
            self.history = self.history[-4:]
        historial_texto = "\n".join(self.history)
        prompt_final = f"{SYSTEM_PROMPT}{contexto_extra}\n\nHISTORIAL DE CONVERSACIÓN:\n{historial_texto}\nCimarrón:"

        payload = {
            "model": self.model_name,
            "prompt": prompt_final,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 250,
                "num_ctx": 4096 # Ampliado a 4096 tokens para que quepa todo el .txt
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
                self.history.append(f"Cimarrón: {text}")
                return text
            else:
                logger.error(f"Ollama retornó código {response.status_code}: {response.text}")
                return "¡Hola! Qué gusto saludarte. La ingeniería en la UABC es asombrosa."
        except Exception as e:
            logger.error(f"Error al comunicar con Ollama local: {e}")
            return "¡Hola! Bienvenido a la Facultad de Ingeniería de la UABC. Estoy aquí para ayudarte."

    def add_knowledge(self, new_text: str) -> bool:
        try:
            txt_path = os.path.join(os.path.dirname(__file__), "conocimiento.txt")
            with open(txt_path, "a", encoding="utf-8") as f:
                f.write(f"\n\n{new_text}")
                
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", ".", " "]
            )
            chunks = text_splitter.split_text(new_text)
            docs = [Document(page_content=c) for c in chunks]
            
            if self.vectorstore is not None:
                self.vectorstore.add_documents(docs)
                logger.info(f"Se inyectaron {len(docs)} fragmentos nuevos en tiempo real.")
                return True
        except Exception as e:
            logger.error(f"Error agregando conocimiento: {e}")
        return False

cimarron_agent = CimarronAgent()
