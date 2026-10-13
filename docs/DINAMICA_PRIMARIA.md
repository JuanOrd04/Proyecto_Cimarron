# Dinámica de primaria

El botón **Iniciar juego** está arriba de Preguntas rápidas. Pide el grado (primero a sexto) y la materia, inicia una ronda de cinco preguntas y termina con el número de respuestas acertadas.

## Flujo de uso

1. Pulsa **Iniciar juego**.
2. Elige el grado y una materia: Matemáticas, Ciencias naturales, Geografía, Biología, Español o Un poco de todo.
3. Pulsa **¡Vamos a jugar!**. El Cimarrón lee la pregunta y sus opciones.
4. Responde con un botón, escribiendo o utilizando el micrófono. Puedes decir el texto de una opción, números como «seis» o «opción B». «No sé» permite recibir la explicación y continuar.
5. El Cimarrón da retroalimentación y una explicación. Pulsa **Siguiente pregunta** para continuar.
6. Después de cinco preguntas aparece el resultado. Puedes jugar otra vez o volver al chat en cualquier momento.

## Contenido y dificultad

- Las preguntas de Ciencias naturales, Geografía, Biología y Español utilizan un banco de 60 preguntas con sus respuestas y explicaciones. Se distribuyen en tres niveles: primero–segundo, tercero–cuarto y quinto–sexto. Las opciones se mezclan al iniciar una ronda.
- Matemáticas genera problemas con resultados calculados: sumas y restas para primero–segundo, multiplicación y división para tercero–cuarto, fracciones sencillas para quinto y porcentajes para sexto.
- Un poco de todo incluye una pregunta de cada una de las cinco materias.
- El contenido es una dinámica general de práctica, no una alineación certificada con un programa escolar específico.

La dinámica utiliza preguntas y respuestas verificables para que la puntuación no dependa de una evaluación improvisada del LLM. La voz usa el mismo Supertonic del chat. Los documentos de la UABC y la caché del chat no se modifican al jugar.

La respuesta escrita o transcrita debe identificar una opción: no se evalúan explicaciones libres extensas. Si no se reconoce, se pide elegir o reformular sin descontar una pregunta. La calidad y disponibilidad del reconocimiento de voz dependen del navegador, igual que en el chat habitual.

## Implementación

- `backend/quiz_engine.py`: contenido, dificultad, selección de opciones, evaluación y sesiones independientes.
- `backend/quiz_api.py`: endpoints `POST /quiz/start`, `/quiz/answer`, `/quiz/next` y `/quiz/end`, con audio.
- `frontend/src/components/QuizPanel.jsx`: selección de grado y materia, opciones, progreso, explicación y resultado.
- `frontend/src/App.jsx`: integra la dinámica, reproduce su voz y dirige las respuestas al modo activo.

Las sesiones no requieren nombres ni cuentas. Se conservan en memoria durante un máximo de dos horas de inactividad y se eliminan al terminar desde la interfaz o reiniciar el backend. Los reintentos de una respuesta no suman puntos dos veces; los reintentos de «Siguiente» no saltan preguntas.

## Arranque

Usa los mismos comandos de la aplicación. Si el backend estaba abierto antes de actualizar estos archivos, deténlo con `Ctrl+C` y vuelve a iniciarlo para cargar los nuevos endpoints.

En Mac–Windows, también se necesita actualizar el backend de la Mac y el frontend del cliente. Las rutas `/quiz` usan la dirección configurable y el intermediario `/api` ya preparados para la conexión.

## Verificación

```bash
cd backend
./venv/bin/python -m unittest discover -s tests -v
```

Las pruebas cubren los seis grados y todas las selecciones de materia, rondas de cinco preguntas, puntuación, respuestas incorrectas, texto y números transcritos, reintentos y separación entre participantes.
