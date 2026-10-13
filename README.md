# Proyecto Cimarrón UABC 🐏

Este es un asistente virtual que hicimos para que los niños de primaria y secundaria (y el público en general) interactúen con el Cimarrón, la mascota de la Facultad de Ingeniería de la UABC. 

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

La configuración local sigue siendo la predeterminada. Para usar la Mac como servidor y una PC Windows como cliente, consulta [la guía de conexión](docs/CONEXION_MAC_WINDOWS.md). Incluye los comandos locales, `iniciar_servidor_mac.sh` e `iniciar_cliente_windows.bat`.

## Dinámica de primaria

El botón **Iniciar juego**, arriba de Preguntas rápidas, prepara una ronda de cinco preguntas según el grado y la materia. El Cimarrón lee las preguntas, explica las respuestas y muestra el resultado final. Consulta [la guía de la dinámica](docs/DINAMICA_PRIMARIA.md).
