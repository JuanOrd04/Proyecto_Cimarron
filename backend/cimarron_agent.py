import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CimarronAgent")

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "qwen2.5-coder:7b"

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

    def generate_response(self, user_message: str) -> str:
        """
        Envía la consulta a Ollama ejecutando el modelo localmente.
        """
        payload = {
            "model": self.model_name,
            "prompt": f"{SYSTEM_PROMPT}\n\nNiño/Pregunta: {user_message}\nCimarrón:",
            "stream": False,
            "options": {
                "temperature": 0.6,
                "num_predict": 75,
                "num_ctx": 512
            }
        }
        
        try:
            logger.info(f"Enviando consulta a Ollama ({self.model_name})...")
            response = requests.post(self.ollama_url, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                text = result.get("response", "").strip()
                # Enforce cleanliness
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
