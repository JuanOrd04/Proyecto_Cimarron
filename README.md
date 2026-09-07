# 🐐 Asistente Interactivo "Cimarrón" UABC

**Facultad de Ingeniería - Universidad Autónoma de Baja California (UABC)**  
Asistente virtual interactivo 100% local y offline diseñado para niños de primaria y secundaria que visitan el campus.

---

## 🚀 Características Principales

- **100% Local & Offline**: Operación total sin conexión a Internet, sin servicios en la nube ni APIs de pago.
- **Frontend Interactivo (React + Vite)**:
  - **Avatar 3D Interactivo**: Inclinación dinámica según la posición del cursor (*Mouse Tilt 3D*), flotación/respiración continua (*idle*) y animación de brinco al hacer clic.
  - **Sincronización de Boca (Lip Sync)**: Alternancia visual entre `cimarron_boca_cerrada.png` y `cimarron_boca_abierta.png` mientras el audio habla.
  - **Entrada por Voz**: Integración con Web Speech API (`webkitSpeechRecognition`) y teclado.
  - **Preguntas Rápidas**: Accesos directos con temas de ingeniería pensados para niños.
- **Backend de Alta Velocidad (FastAPI + Python)**:
  - **LLM Local con Ollama**: Modelo `qwen2.5-coder:7b` guiado por un System Prompt con personalidad alegre, entusiasta, explicaciones sencillas de ingeniería y respuestas de **máximo 2 oraciones**.
  - **TTS Local**: Generación de audio en formato WAV codificado en Base64 retornado directamente en el endpoint `/chat`.

---

## 💻 Requisitos del Sistema

- **GPU recomendada**: NVIDIA GeForce RTX 4060 (8 GB VRAM) o superior.
- **Ollama**: Instalado localmente con el modelo `qwen2.5-coder:7b`.
- **Node.js**: v18+ y npm.
- **Python**: v3.10+.

---

## 🛠️ Instrucciones de Ejecución

### ⚡ Inicio en 1 Clic (Recomendado)
Haz doble clic en el archivo maestro en la raíz del proyecto o ejecútalo en tu terminal:
```cmd
iniciar_todo.bat
```
Este script automáticamente:
1. Inicia el backend en `http://127.0.0.1:8000`.
2. Inicia el frontend en `http://127.0.0.1:5173`.
3. Abre tu navegador automáticamente en la aplicación.

---

### Inicio Manual por Separado
Si prefieres correrlos en terminales separadas:

---

## 🎨 Estructura del Proyecto

```
Proyecto_Cimarron/
├── backend/
│   ├── main.py                 # API FastAPI (endpoints /chat y /health)
│   ├── cimarron_agent.py       # Agente de Ollama con System Prompt del Cimarrón UABC
│   ├── tts_engine.py           # Motor TTS local (generador de WAV en Base64)
│   ├── requirements.txt        # Dependencias de Python
│   └── start_backend.bat       # Script de inicio rápido del backend
├── frontend/
│   ├── public/
│   │   ├── cimarron_boca_cerrada.png
│   │   └── cimarron_boca_abierta.png
│   ├── src/
│   │   ├── components/
│   │   │   ├── CimarronAvatar.jsx   # Avatar 3D, animación float, brinco y boca
│   │   │   ├── SpeechBubble.jsx     # Globo de diálogo cómic UABC
│   │   │   ├── SpeechButton.jsx     # Micrófono Web Speech API y entrada de texto
│   │   │   └── QuickQuestions.jsx   # Botones de preguntas predefinidas
│   │   ├── App.jsx                  # Estado global y sincronización de audio/boca
│   │   ├── App.css                  # Estilos visuales institucionales UABC
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── start_frontend.bat      # Script de inicio rápido del frontend
└── README.md
```
