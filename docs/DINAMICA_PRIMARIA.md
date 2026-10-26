# Dinámica de primaria

El botón **Iniciar juego**, encima de Preguntas rápidas, permite elegir primero a sexto y Matemáticas, Ciencias naturales, Geografía, Biología, Español o Un poco de todo. La ronda termina tras cinco preguntas con resultado final.

## Uso

1. Elige grado y materia. El indicador muestra cuántas preguntas hay disponibles; como salen del banco, la ronda está lista de inmediato. Pulsa **Comenzar**.
2. Cada pregunta muestra cuatro tarjetas de colores con letras A–D.
3. El Cimarrón lee la pregunta y sus opciones y abre el micrófono. Pulsa una tarjeta, di su letra, responde con tus palabras o escribe. Puedes pulsar una opción mientras se narra la pregunta. Puedes decir «creo que…», corregirte («la luna… no, espera, el sol»), pedir que te la repita o decir «no sé».
4. Tras la retroalimentación pasa automáticamente a la siguiente pregunta. Si no se entendió la respuesta, conserva la pregunta y pide la letra o la respuesta otra vez.
5. El botón del micrófono pausa la escucha y el avance automáticos; puedes escribir y pulsar Siguiente. Pulsarlo otra vez los reanuda.
6. Al terminar muestra aciertos sobre cinco. Puedes jugar otra vez o volver al chat.

El permiso de micrófono puede requerir una acción del usuario. Ante silencio, error o permiso rechazado se pausa el modo automático para evitar un bucle de escucha. La transcripción sigue dependiendo del navegador, incluso sin internet.

## De dónde salen las preguntas

Del banco revisado [backend/data/banco_preguntas.json](../backend/data/banco_preguntas.json): 298 preguntas (borrador por revisar con el maestro) con respuesta, tres distractores, explicación, pista, materia y rango de grados. «Un poco de todo» toma una pregunta de cada materia; una materia sola toma cinco preguntas distintas de ese grado. El programa recuerda qué preguntas ya salieron, aunque se reinicie, y elige primero las que menos se han usado, así que no se repiten hasta recorrer el banco. Las opciones se mezclan con un orden fijo por pregunta, así que la respuesta correcta no está siempre en la misma letra y la voz puede prepararse una sola vez. Para agregar o corregir preguntas consulta [la guía del banco](GENERACION_PREGUNTAS.md).

## Qué hace el modelo

El LLM local `qwen2.5:7b` (el chat sigue con `gemma2:2b`) solo interpreta lo que responde el niño:

- **Opciones de texto.** Un árbitro recibe las cuatro opciones y lo que dijo el niño, sin ver la pregunta, y decide qué opción quiso decir por su significado: la letra, el texto, un sinónimo, un diminutivo o una descripción. Así no puede inclinarse hacia la respuesta correcta. Después Python compara la opción elegida con la respuesta.
- **Respuestas fuera de las opciones o «no sé».** Un juez, que sí ve la pregunta y la respuesta esperada, decide si lo que dijo el niño también es correcto.
- **Números.** El modelo solo anota el número que dijo el niño, sin ver el problema, y Python lo compara con la respuesta.

No hay listas de variantes infantiles ni un comparador literal de textos. La retroalimentación no la escribe el modelo: son frases fijas armadas con la explicación del banco («¡Muy bien!…» o «Buen intento. La respuesta es…»).

- `correct`: un acierto y avance después de la narración.
- `incorrect`: explicación sin acierto y avance. Decir «no sé» cuenta como incorrecto, salvo que el juez reconozca una respuesta válida.
- `unclear`: pedir repetir, ruido, dudar entre dos opciones o pedir el punto. Repite la pregunta o pide aclarar, manteniendo el turno sin sumar ni restar.

Los reintentos no duplican puntos ni saltan turnos, y no se mezclan participantes. Un fallo de Ollama conserva la pregunta pendiente. El diseño completo está en [la arquitectura](ARQUITECTURA_IA.md).

## Preparar la demostración

1. Instala los modelos en Ollama: `ollama pull qwen2.5:7b` para el juego y `gemma2:2b` para el chat. `GET /health` del backend indica si el modelo del juego está instalado.
2. Inicia Cimarrón con los comandos habituales. Al arrancar, el backend sintetiza en segundo plano las voces de las preguntas que falten y las guarda en `backend/quiz_audio.sqlite3`. La primera vez en una computadora tarda más; conviene arrancarlo antes de recibir niños. En los arranques siguientes las voces ya están guardadas.
3. Juega una ronda de prueba con el micrófono del lugar.

No hay que preparar rondas por grado ni por materia: el banco sirve para todos los perfiles desde el arranque. Las sesiones y respuestas de los niños solo se guardan en memoria.

En Mac–Windows se deben actualizar backend y frontend, y la Mac que funciona como servidor necesita `qwen2.5:7b`. Se conserva el proxy configurable existente.

## Verificación y límites

```bash
cd backend
./venv/bin/python -m unittest discover -s tests -v
./venv/bin/python scripts/check_interpretation_live.py
./venv/bin/python scripts/check_interpretation_live.py tests/fixtures/respuestas_ninos_validacion.json
```

Las pruebas unitarias usan dobles del modelo y de la voz; comprueban el banco, las rondas por grado y materia, el audio guardado, la puntuación, la concurrencia y los errores. Los otros dos comandos usan Ollama real y miden la interpretación con respuestas de ejemplo: en la última medición acertó 102 de 105 casos y 85 de 87 en el conjunto de validación.

```bash
cd frontend
npm test
npm run build
```

Las pruebas de voz simulan eventos del reconocedor. Debe revisarse el micrófono físico en el navegador de la feria. Los casos de ejemplo son frases escritas para el proyecto, no grabaciones de niños: no miden errores del reconocimiento de voz ni ruido de fondo. El banco es pequeño y sus rangos de grado son decisiones del proyecto que requieren revisión docente. La interpretación puede equivocarse.

## Presentación con cuatro tarjetas

La interfaz muestra una cuadrícula de dos por dos con tarjetas roja, azul, amarilla y verde, identificadas por las letras grandes A, B, C y D y el texto de cada respuesta. Durante la retroalimentación se conservan las letras y opciones y se destaca la respuesta correcta indicada por el servidor.

El Cimarrón aparece grande junto a la pregunta y dentro del panel de selección de grado y materia. La narración incluye las cuatro opciones y se reutiliza, con el mismo audio, al pedir repetir.

`QuizAnswers.jsx` gestiona las tarjetas. Pulsar una tarjeta envía su texto por la misma ruta que una respuesta hablada. `quiz_narration.py` mantiene una única representación hablada de la pregunta para preparar su voz, mostrarla y repetirla. La letra correcta que se destaca se calcula después de calificar; no se usa para interpretar lo que dijo el niño.
