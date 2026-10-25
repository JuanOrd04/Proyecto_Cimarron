import os

import requests

from inference_queue import InferenceQueue


MODEL_NAME = 'gemma2:2b'
# El juego necesita seguir instrucciones y elegir entre opciones con precisión;
# qwen2.5:7b lo hace mucho mejor que gemma2:2b. Se puede cambiar sin tocar código.
QUIZ_MODEL_NAME = os.getenv('CIMARRON_QUIZ_MODEL', 'qwen2.5:7b')
OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
OLLAMA_URL = f'{OLLAMA_BASE_URL}/api/generate'


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, model_name=MODEL_NAME, url=OLLAMA_URL, post=None):
        self.model_name = model_name
        self.url = url
        self.post = post or requests.post
        self.queue = InferenceQueue()

    def generate(self, prompt, options=None, schema=None, timeout=120, priority='interactive', system=None):
        payload = {
            'model': self.model_name,
            'prompt': prompt,
            'stream': False,
            'keep_alive': '30m',
            'options': options or {'temperature': 0.1, 'num_predict': 250, 'num_ctx': 4096},
        }
        if schema is not None:
            payload['format'] = schema
        if system is not None:
            payload['system'] = system
        try:
            with self.queue.acquire(priority, timeout) as remaining:
                response = self.post(self.url, json=payload, timeout=remaining)
            response.raise_for_status()
            data = response.json()
            text = data.get('response', '')
            if not isinstance(text, str) or data.get('done') is False:
                raise ValueError('Respuesta inválida de Ollama.')
            if schema is not None and data.get('done_reason') == 'length':
                raise ValueError('Respuesta incompleta de Ollama.')
            return text.strip()
        except (requests.RequestException, ValueError, TypeError, AttributeError, TimeoutError) as exc:
            raise OllamaError('No se pudo obtener una respuesta de Ollama.') from exc


ollama_client = OllamaClient()
quiz_client = ollama_client if QUIZ_MODEL_NAME == MODEL_NAME else OllamaClient(model_name=QUIZ_MODEL_NAME)
