# Banco de preguntas: contenido, voces y cómo agregar preguntas

Las preguntas del juego ya no se generan con el LLM. Salen de un banco revisado, [backend/data/banco_preguntas.json](../backend/data/banco_preguntas.json), que cualquier docente puede corregir o ampliar editando el archivo. El modelo local (`qwen2.5:7b`) solo interpreta lo que responde el niño; ese diseño está explicado en [la guía de IA](ARQUITECTURA_IA.md). Este archivo conserva su nombre porque el README lo enlaza, pero ahora es la guía del banco.

## Por qué ya no se generan

La versión anterior pedía a `gemma2:2b` que eligiera un concepto de un corpus recuperado por RAG, redactara la pregunta, propusiera tres distractores y revisara su propio trabajo; todo se preparaba antes de la ronda y se guardaba en una caché. Funcionaba, pero se observaron preguntas mal formuladas que el mismo modelo aprobaba, y una revisión hecha por el mismo modelo no equivale a una revisión docente. Por indicación del maestro se cambió a un banco escrito y revisado por personas: el contenido es fijo y verificable, y el trabajo de IA se concentra en interpretar respuestas habladas. Los módulos de generación (`quiz_generation.py`, `quiz_preparation.py`, `quiz_cache.py`, `quiz_knowledge.py`) siguen en disco pero el juego ya no los usa.

## Qué contiene

96 preguntas de opción múltiple, cada una con su respuesta, tres distractores y una explicación breve.

| Materia | Preguntas | Reparto por grado |
| --- | --- | --- |
| Matemáticas | 36 | 6 por cada grado, de primero a sexto |
| Ciencias naturales | 15 | 5 para 1.º–2.º, 5 para 3.º–4.º, 5 para 5.º–6.º |
| Geografía | 15 | igual |
| Biología | 15 | igual |
| Español | 15 | igual |

Una ronda tiene cinco preguntas. En «Un poco de todo» toca una de cada materia, en orden aleatorio; en una materia sola, cinco preguntas distintas de esa materia cuyo rango incluya el grado elegido. Con el banco actual, una materia que no sea Matemáticas tiene exactamente cinco preguntas por rango, así que un niño que elija, por ejemplo, Geografía de segundo siempre recibe las mismas cinco (cambia el orden). Agregar preguntas es la forma de dar variedad.

38 preguntas tienen respuesta numérica: las 36 de Matemáticas, «¿Cuántas patas tiene un insecto adulto?» y «¿Cuántas sílabas tiene la palabra mesa?».

## Formato de cada pregunta

```json
{
  "id": "cn-12-01",
  "subject": "ciencias_naturales",
  "min_grade": 1,
  "max_grade": 2,
  "prompt": "¿Qué nos da luz y calor durante el día?",
  "answer": "El Sol",
  "distractors": ["La Luna", "Una piedra", "Una nube"],
  "explanation": "El Sol es una estrella que nos proporciona luz y calor."
}
```

`BankQuestion` en [backend/quiz_bank.py](../backend/quiz_bank.py) valida cada fila al arrancar. Si alguna no cumple, el backend no inicia y el error indica qué campo o qué pregunta falló.

| Campo | Regla |
| --- | --- |
| `id` | Obligatorio y único en todo el banco. Por convención, `materia-rango-número`: `cn-12-01`, `bio-34-04`, `mat-3-01`. Prefijos usados: `mat`, `cn`, `geo`, `bio`, `esp`. |
| `subject` | `matematicas`, `ciencias_naturales`, `geografia`, `biologia` o `espanol`. No se permite `mixto`. |
| `min_grade`, `max_grade` | De 1 a 6, con `min_grade` ≤ `max_grade`. |
| `prompt` | La pregunta, de 5 a 240 caracteres. |
| `answer` | La respuesta correcta, de 1 a 80 caracteres. |
| `distractors` | Exactamente tres respuestas incorrectas. Las cuatro opciones deben ser distintas, sin importar mayúsculas. |
| `explanation` | De 5 a 300 caracteres. Se dice tanto al acertar como al fallar. |

No se admiten campos adicionales.

## Cómo agregar o corregir una pregunta

1. Abre `backend/data/banco_preguntas.json` y agrega un objeto a la lista (o corrige uno existente). Cuida las comas entre objetos.
2. Comprueba el banco desde `backend/`:

   ```bash
   ./venv/bin/python -m unittest tests.test_quiz_bank -v
   ```

   Las pruebas validan el esquema, que no haya ids repetidos y que todos los grados y materias puedan armar una ronda de cinco.
3. Reinicia el backend. Al arrancar sintetiza en segundo plano las voces nuevas o modificadas; las demás se reutilizan.
4. Opcional, para comprobar cómo se interpretan respuestas a la pregunta nueva: agrega casos a `backend/tests/fixtures/respuestas_ninos.json` con la forma `{"bank_id": "cn-12-06", "nino_dijo": "el solecito", "esperado": "correct"}` (`esperado` puede ser `correct`, `incorrect`, `unclear` o `not_correct`) y ejecuta, con Ollama abierto:

   ```bash
   ./venv/bin/python scripts/check_interpretation_live.py
   ```

## Consejos para escribir preguntas

El Cimarrón lee la pregunta y las cuatro opciones en voz alta, y el niño contesta hablando. Eso cambia lo que es una buena pregunta:

- **Opciones cortas y fáciles de decir.** El niño puede contestar con la letra o con el texto; una opción breve es más fácil de recordar y de repetir.
- **Opciones con significados claramente distintos.** El árbitro elige la opción cuyo significado coincide con lo que dijo el niño. Si dos opciones significan casi lo mismo, la interpretación puede confundirse.
- **Sin referencias a la posición.** Las opciones se mezclan, así que no uses «todas las anteriores», «ninguna de las anteriores» ni letras dentro del texto. El orden depende del `id` y es el mismo en todas las partidas; cambiar el `id` cambia el orden y obliga a sintetizar otra vez la voz.
- **Respuestas numéricas solo con dígitos.** Si `answer` contiene solo dígitos (`"10"`), la pregunta usa la ruta numérica: el modelo anota el número que dijo el niño y Python lo compara. En ese caso los tres distractores también deben ser números en dígitos, porque si el niño elige una letra se convierte el texto de esa opción en número. Fracciones, decimales o unidades (`"3.5"`, `"10 cm"`) se tratan como respuesta de texto.
- **Una explicación que sirva en ambos casos.** Se dice después de «¡Muy bien!» y después de «Buen intento. La respuesta es…». Una oración completa que explique el porqué funciona mejor que repetir la respuesta.
- **Una sola respuesta correcta.** Si el niño propone algo fuera de las opciones, un juez decide si también es válido. Aun así, la pregunta debe tener una respuesta inequívoca entre las cuatro.

## Voces

`BankQuestionProvider.warm_audio()` corre al arrancar el backend. Para cada pregunta sintetiza tres audios con Supertonic, la narración con sus opciones, la retroalimentación de acierto y la de error, y los guarda en `backend/quiz_audio.sqlite3`. Este archivo está excluido de Git: cada computadora lo crea la primera vez que arranca, lo que tarda más que los arranques siguientes.

La clave de cada audio es un hash del texto y de `tts_engine.py`. Corregir una pregunta solo vuelve a sintetizar sus textos; cambiar la configuración de la voz vuelve a sintetizar todo. Los audios viejos no se borran solos; para empezar de cero basta con borrar el archivo con el backend apagado. Si un niño empieza antes de que termine la síntesis, la API genera la voz que falte en el momento.

## Límites

- El banco es pequeño. Cubre los seis grados y las cinco materias, pero con pocas preguntas por combinación; se repiten entre partidas.
- Los rangos de grado y la redacción son decisiones del proyecto; requieren revisión docente y no representan una certificación curricular.
- La interpretación de respuestas es falible: en las mediciones registradas acierta 102 de 105 y 85 de 87 casos de ejemplo, escritos para el proyecto, no grabados en la feria.
