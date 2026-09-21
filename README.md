# Proyecto Cimarrón UABC 🐏

Este es un asistente virtual que hicimos para que los niños de primaria y secundaria (y el público en general) interactúen con el Cimarrón, la mascota de la Facultad de Ingeniería de la UABC. 

## ¿Qué hace el proyecto?
- Responde preguntas sobre las ingenierías usando Inteligencia Artificial local (Ollama).
- Habla en voz alta y mueve la boca al contestar.
- Toda la información la saca de una base de datos local (ChromaDB) para no inventar cosas y que sea información real de la facultad.
- Funciona 100% offline, así que no necesitamos pagar APIs ni tener internet en los eventos.

## ¿Cómo correr el proyecto?

**1. Backend (El cerebro)**
Abre una terminal, activa el entorno virtual, instala las dependencias y crea la base vectorial. La ingestión utiliza `backend/conocimiento.txt` y todos los archivos `.txt` dentro de `backend/data` y sus subcarpetas:
```bash
cd backend
venv\Scripts\activate
pip install -r requirements.txt
python ingest_knowledge.py
uvicorn main:app --reload
```

Vuelve a ejecutar `python ingest_knowledge.py` cada vez que agregues o modifiques un archivo de conocimiento. Detén el backend antes de reconstruir la base.

**2. Frontend (La interfaz)**
Abre otra terminal y levanta la página en React:
```bash
cd frontend
npm run dev
```

Y listo, ya puedes abrir la página y platicar con el Cimarrón.
