import os
import tempfile
import base64
import wave
import math
import struct
import logging

try:
    from supertonic import TTS
    SUPERTONIC_AVAILABLE = True
except ImportError:
    SUPERTONIC_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TTS_Engine")

class LocalTTSEngine:
    def __init__(self):
        self.tts = None
        self.style = None
        self._init_supertonic()

    def _init_supertonic(self):
        if SUPERTONIC_AVAILABLE:
            try:
                # Inicializar Supertonic TTS (ONNX)
                self.tts = TTS(auto_download=True)
                # Seleccionar una voz masculina para el Cimarrón ("M1", "M2", etc.)
                self.style = self.tts.get_voice_style(voice_name="M1")
                logger.info(f"Supertonic 3 TTS configurado con éxito.")
            except Exception as e:
                logger.warning(f"No se pudo inicializar Supertonic TTS: {e}. Se utilizará el generador WAV de respaldo.")
                self.tts = None
        else:
            logger.warning("Librería 'supertonic' no instalada. Se utilizará el generador WAV de respaldo.")

    def synthesize_to_base64_wav(self, text: str) -> str:
        """
        Sintetiza texto a audio WAV localmente usando Supertonic 3 y retorna un Data URI en Base64.
        """
        if self.tts and self.style:
            try:
                # Generar audio con Supertonic (Soporta español con lang="es")
                wav, duration = self.tts.synthesize(
                    text=text,
                    voice_style=self.style,
                    lang="es"
                )
                
                # Guardar el audio usando el método integrado de supertonic
                if wav is not None:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                        tmp_path = tmp_file.name
                    
                    self.tts.save_audio(wav, tmp_path)
                    
                    if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                        with open(tmp_path, "rb") as f:
                            wav_bytes = f.read()
                        os.remove(tmp_path)
                        b64_str = base64.b64encode(wav_bytes).decode("utf-8")
                        return f"data:audio/wav;base64,{b64_str}"
            except Exception as e:
                logger.error(f"Error durante síntesis con Supertonic TTS: {e}")
                if 'tmp_path' in locals() and os.path.exists(tmp_path):
                    os.remove(tmp_path)

        # Respaldo: generar tono sintetizado de confirmación
        return self._generate_fallback_beep_wav()

    def _generate_fallback_beep_wav(self) -> str:
        """Genera un archivo WAV en memoria como tono de respuesta si falla TTS."""
        sample_rate = 16000
        duration = 0.5  # segundos
        num_samples = int(sample_rate * duration)
        
        raw_data = bytearray()
        for i in range(num_samples):
            val = int(16000 * math.sin(2 * math.pi * 440 * i / sample_rate))
            raw_data.extend(struct.pack('<h', val))

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        with wave.open(tmp_path, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(raw_data)

        with open(tmp_path, 'rb') as f:
            wav_bytes = f.read()
        os.remove(tmp_path)

        b64_str = base64.b64encode(wav_bytes).decode("utf-8")
        return f"data:audio/wav;base64,{b64_str}"

# Instancia global reutilizable
tts_service = LocalTTSEngine()
