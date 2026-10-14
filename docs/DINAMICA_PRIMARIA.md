# Dinámica de primaria

El botón **Iniciar juego** está arriba de Preguntas rápidas. Pide el grado (primero a sexto) y la materia, inicia una ronda de cinco preguntas y termina con el número de respuestas acertadas.

## Flujo de uso

1. Pulsa **Iniciar juego**.
2. Elige el grado y una materia: Matemáticas, Ciencias naturales, Geografía, Biología, Español o Un poco de todo.
3. Pulsa **¡Vamos a jugar!**. El Cimarrón lee la pregunta y sus opciones.
4. Al terminar de leer, abre automáticamente el micrófono. Responde hablando con tus propias palabras, con un botón o escribiendo. Puedes explicar tu idea, decir «creo que…», mencionar números como «seis» o elegir «opción B». «No sé» permite recibir la explicación y continuar.
5. El micrófono se cierra al enviar la respuesta. El Cimarrón da retroalimentación y una explicación; al terminar de leerla pasa automáticamente a la siguiente pregunta y vuelve a abrir el micrófono cuando termine de hablar.
6. Si tu respuesta es incompleta o poco clara, el Cimarrón pide completar o aclarar: mantiene la misma pregunta, no cambia la puntuación y vuelve a abrir el micrófono después de hablar. Puede combinar tu siguiente respuesta con lo dicho antes en esa pregunta.
7. Después de cinco preguntas aparece el resultado. Puedes jugar otra vez o volver al chat en cualquier momento.

## Contenido y dificultad

- Las preguntas de Ciencias naturales, Geografía, Biología y Español utilizan un banco de 60 preguntas con sus respuestas y explicaciones. Se distribuyen en tres niveles: primero–segundo, tercero–cuarto y quinto–sexto. Las opciones se mezclan al iniciar una ronda.
- Matemáticas genera problemas con resultados calculados: sumas y restas para primero–segundo, multiplicación y división para tercero–cuarto, fracciones sencillas para quinto y porcentajes para sexto.
- Un poco de todo incluye una pregunta de cada una de las cinco materias.
- El contenido es una dinámica general de práctica, no una alineación certificada con un programa escolar específico.

## Interpretación de respuestas con LLM

Las preguntas y respuestas esperadas del banco siguen siendo referencias educativas. **La evaluación de las respuestas libres y la retroalimentación ahora se realizan con un LLM local mediante Ollama**, no con coincidencias de texto ni expresiones regulares. Este avance no genera preguntas nuevas con el LLM: incorpora comprensión por significado a las preguntas actuales.

El evaluador recibe el grado, la pregunta, sus opciones, la respuesta mínima correcta, la explicación de referencia y hasta tres turnos de aclaración de esa misma pregunta. La respuesta infantil se envía íntegra (hasta 2000 caracteres). El chat de la UABC conserva su propio historial y su modelo.

Se usa `qwen2.5:7b` de forma predeterminada para la dinámica. Puede configurarse antes de iniciar el backend con `CIMARRON_QUIZ_MODEL`; el modelo elegido debe estar instalado en Ollama. La API pide una salida JSON mediante un esquema de Pydantic, con estado, interpretación, número identificado cuando corresponda y retroalimentación. Un esquema comprueba la estructura, no garantiza la corrección del juicio.

- `correct`: cuenta un acierto y permite pasar a la siguiente pregunta.
- `incorrect`: explica la respuesta y permite continuar, sin sumar un acierto.
- `partial`: reconoce lo aportado y pide la parte esencial que falta; no consume la pregunta.
- `unclear`: solicita una aclaración neutral; no consume la pregunta.

El LLM identifica el significado y, en preguntas numéricas, el número elegido. Python compara ese número con el resultado calculado para evitar una calificación matemática contradictoria. Si Ollama falla, tarda demasiado o devuelve datos inválidos, la API responde con un error y conserva la pregunta: no sustituye silenciosamente al modelo por un comparador de texto.

El modelo también cita fragmentos de lo dicho por el alumno. El programa comprueba que esas citas existan en el texto recibido, sin compararlas con las palabras de la respuesta correcta. Si el modelo parafrasea una cita en vez de copiarla, otra consulta semántica breve busca el fragmento original (por ejemplo, «perrito» para la idea «perro»); si no puede respaldar la interpretación, pide aclarar. Esta comprobación evita aceptar una respuesta que el modelo haya inventado, pero no garantiza por sí sola la precisión semántica.

Las evaluaciones son independientes por participante; los reintentos de respuestas ya calificadas no llaman otra vez al LLM ni duplican puntos. Una evaluación pendiente no mantiene bloqueadas las otras sesiones. La voz sigue usando Supertonic. Los documentos y la caché del chat de la UABC no se modifican al jugar.

La disponibilidad y calidad de la transcripción siguen dependiendo del navegador. La interpretación por LLM tampoco garantiza que todas las respuestas ambiguas se califiquen bien: deben revisarse ejemplos representativos para la feria, especialmente negaciones, respuestas incompletas y transcripciones incorrectas.

## Modo de voz

El modo de voz se activa al iniciar cada ronda. **Pausar voz** desactiva la escucha y el avance automáticos; **Reanudar voz** los activa de nuevo. En modo pausado puedes usar **Hablar**, escribir o elegir opciones y pulsar **Siguiente pregunta**. Al salir del juego o llegar al resultado final no se abre el micrófono.

El navegador puede solicitar permiso de micrófono la primera vez. Si lo rechaza, no reconoce voz, no escucha una respuesta o no puede reproducir el audio, se muestra un aviso y se pausa el modo automático para evitar reintentos continuos. Puedes reanudarlo o seguir con botones. Detener el micrófono descarta una transcripción incompleta; detener la narración pausa el modo automático. La transcripción se envía una sola vez y el micrófono se cierra antes de reproducir la explicación.

El reconocimiento sigue utilizando la Web Speech API existente del navegador: **abrirlo automáticamente no convierte la transcripción en un servicio local sin internet**. El juego y su voz sintetizada siguen funcionando localmente; la disponibilidad de transcripción sin internet depende del navegador. En el cliente Windows se conserva el acceso mediante su frontend local y el proxy hacia la Mac.

## Implementación

- `backend/quiz_engine.py`: contenido de referencia, dificultad, opciones, puntuación y sesiones independientes.
- `backend/quiz_llm.py`: interpretación por significado, retroalimentación y comprobación estructurada de la respuesta del LLM.
- `backend/quiz_api.py`: endpoints `POST /quiz/start`, `/quiz/answer`, `/quiz/next` y `/quiz/end`, con audio.
- `frontend/src/components/QuizPanel.jsx`: selección de grado y materia, opciones, progreso, explicación y resultado.
- `frontend/src/App.jsx`: integra la dinámica, reproduce su voz y dirige las respuestas al modo activo.
- `frontend/src/components/SpeechButton.jsx` y `frontend/src/utils/speechRecognitionSession.js`: apertura automática, cancelación y entrega de una sola respuesta por sesión de escucha.

Las sesiones no requieren nombres ni cuentas. Se conservan en memoria durante un máximo de dos horas de inactividad y se eliminan al terminar desde la interfaz o reiniciar el backend. Los reintentos de una respuesta no suman puntos dos veces; los reintentos de «Siguiente» no saltan preguntas.

## Arranque

Primero descarga el modelo de la dinámica una sola vez, con internet:

```bash
ollama pull qwen2.5:7b
```

Una vez descargado, la evaluación se ejecuta localmente y no necesita internet. La transcripción del micrófono conserva sus dependencias del navegador.

Usa los mismos comandos de la aplicación. Si el backend estaba abierto antes de actualizar estos archivos, deténlo con `Ctrl+C` y vuelve a iniciarlo para cargar los nuevos endpoints.

En Mac–Windows, también se necesita actualizar el backend de la Mac y el frontend del cliente. Las rutas `/quiz` usan la dirección configurable y el intermediario `/api` ya preparados para la conexión.

## Verificación

```bash
cd backend
./venv/bin/python -m unittest discover -s tests -v
```

Las pruebas unitarias usan un evaluador simulado y cubren los seis grados, las materias, rondas completas, puntuación, aclaraciones, respuestas largas, fallos del modelo, datos inválidos, cálculo numérico, reintentos concurrentes y separación entre participantes. Estas pruebas validan la integración; la calidad semántica se comprueba por separado con Ollama real.

Para ejecutar los ejemplos semánticos con el modelo instalado (paráfrasis, respuestas incompletas, negación, números, correcciones y aclaraciones):

```bash
cd backend
./venv/bin/python scripts/check_quiz_llm_live.py
```

El script verifica las clasificaciones esperadas y muestra la retroalimentación para revisión. No constituye una garantía de precisión general ni una prueba de transcripción con micrófono físico. `/health` informa también `quiz_model` y `quiz_model_status` para verificar la configuración del evaluador.

Para verificar las sesiones de escucha (cancelación, respuestas duplicadas, errores y silencio):

```bash
cd frontend
npm test
npm run build
```

Estas pruebas simulan los eventos del reconocedor; la calidad de transcripción de un micrófono físico debe comprobarse en el navegador que se usará en la feria.
