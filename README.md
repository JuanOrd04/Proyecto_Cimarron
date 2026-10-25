# Proyecto Cimarrón UABC 🐏

Este es un asistente virtual que hicimos para que los niños de primaria y secundaria (y el público en general) interactúen con el Cimarrón, la mascota de la Facultad de Ingeniería de la UABC. 

## Organización del proyecto

```text
Proyecto_Cimarron/
├── backend/     API, IA, contexto, datos, pruebas y dependencias de Python
├── frontend/    Interfaz, imágenes y pruebas del navegador
├── docs/        Guías de uso, arquitectura e historial del proyecto
├── scripts/     Lanzadores de Mac, Windows y WSL; conversor de imágenes
└── README.md
```

Las guías del juego y de la arquitectura están en `docs/`. El archivo de versiones de la instalación de Python en macOS está en `backend/requirements-macos.lock.txt`; `backend/requirements.txt` conserva las dependencias habituales.

## ¿Qué hace el proyecto?
- Responde preguntas sobre las ingenierías usando Inteligencia Artificial local (Ollama).
- Habla en voz alta y mueve la boca al contestar.
- Toda la información la saca de una base de datos local (ChromaDB) para no inventar cosas y que sea información real de la facultad.
- Funciona 100% offline, así que no necesitamos pagar APIs ni tener internet en los eventos.

## ¿Cómo correr el proyecto?

**1. Backend (El cerebro)**
Abre una terminal, activa el entorno virtual y corre el servidor de Python:
```bash
cd backend
venv\Scripts\activate
uvicorn main:app --reload
```

**2. Frontend (La interfaz)**
Abre otra terminal y levanta la página en React:
```bash
cd frontend
npm run dev
```

Y listo, ya puedes abrir la página y platicar con el Cimarrón.

## Ejecutar en Mac o conectar un cliente Windows

La configuración local sigue siendo la predeterminada. Para usar la Mac como servidor y una PC Windows como cliente, inicia `scripts/iniciar_servidor_mac.sh` en la Mac y `scripts/iniciar_cliente_windows.bat` en Windows, pasando la dirección de la Mac (por ejemplo `iniciar_cliente_windows.bat http://192.168.1.50:8000`).

Desde la raíz del proyecto, `bash scripts/iniciar_todo.sh` inicia los dos servicios mediante Bash. `scripts/iniciar_todo.bat` conserva el lanzador original para WSL y su ruta `/home/zombs/Proyecto_Cimarron`. El conversor de imágenes se ejecuta con `python scripts/convert_images.py` y requiere Pillow en ese entorno de Python.

## Dinámica de primaria

El botón **Iniciar juego**, arriba de Preguntas rápidas, prepara una ronda de cinco preguntas según el grado y la materia. El Cimarrón lee las preguntas, explica las respuestas y muestra el resultado final. Consulta [la guía de la dinámica](docs/DINAMICA_PRIMARIA.md).

Las preguntas salen de un banco revisado, `backend/data/banco_preguntas.json` (pregunta, respuesta, tres distractores, explicación, materia y rango de grados); para agregar o corregir preguntas basta con editar ese archivo. Sus voces se sintetizan una sola vez al arrancar y se guardan en `backend/quiz_audio.sqlite3`. El LLM local (`qwen2.5:7b`, configurable con `CIMARRON_QUIZ_MODEL`; el chat sigue con `gemma2:2b`) se dedica a interpretar lo que responde el niño: decide qué opción eligió por el significado de lo que dijo (letra, texto, sinónimo, "creo que…", autocorrecciones), sin ver la pregunta para no inclinarse hacia la respuesta correcta. Si dice otra cosa, el LLM juzga si también es válida; en números extrae la cifra y Python la compara. No se comparan textos. Para medir la interpretación con Ollama real: `cd backend && ./venv/bin/python scripts/check_interpretation_live.py` (y con `tests/fixtures/respuestas_ninos_validacion.json` como argumento para el conjunto de validación). Consulta [el diseño y sus límites](docs/GENERACION_PREGUNTAS.md) y [la guía para explicar el código](docs/ARQUITECTURA_IA.md). La revisión del mismo modelo sigue siendo falible y requiere evaluación docente.
