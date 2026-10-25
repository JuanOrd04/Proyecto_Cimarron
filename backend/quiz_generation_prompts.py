import json

from quiz_curriculum import SUBJECTS


def generation_prompt(grade, subject, document, previous, retry_reason):
    task = (
        'Escribe un problema de UNA sola operación (suma, resta, multiplicación o división) con objetos cotidianos '
        'y resultado entero no negativo. Escribe las cantidades con dígitos y no uses dinero ni unidades de medida. '
        'operacion: solo números y signos + - * / con las cantidades del problema, sin el signo igual. '
        'respuesta_correcta y distractores: solo números enteros distintos. '
    ) if subject == 'matematicas' else (
        'Basa la pregunta y la respuesta correcta SOLO en el dato. '
        'respuesta_correcta: de 1 a 5 palabras. '
        'distractores: tres respuestas del mismo tipo que la correcta, que un niño podría creer, pero claramente falsas. '
    )
    return (
        f'Escribe UNA pregunta de opción múltiple en español de México para un niño de {grade}° de primaria, '
        f'sobre {SUBJECTS[subject]}. Se leerá en voz alta en una feria de ciencia: máximo 20 palabras '
        '(40 en matemáticas), una sola tarea y una sola respuesta correcta. '
        'El niño no ve el dato, imágenes ni mapas: la pregunta debe entenderse sola y no puede decir "según el dato" o "según el texto". '
        'No escribas la respuesta dentro de la pregunta ni pongas las opciones en la pregunta. '
        + task +
        'explicacion: una oración amable de máximo 20 palabras que le explique la respuesta correcta al niño.\n'
        + json.dumps({
            'dato': document.page_content,
            'no_repitas': [question['prompt'] for question in previous if question.get('subject') == SUBJECTS[subject]][-6:],
            'corrige': retry_reason,
        }, ensure_ascii=False) + '\nJSON:'
    )


def blind_answer_prompt(prompt, options):
    return (
        'Responde esta pregunta de opción múltiple de primaria. Razona en una oración corta y elige la ÚNICA opción correcta. '
        'Usa VARIAS si más de una opción es correcta, NINGUNA si ninguna lo es o si la pregunta es confusa.\n'
        + json.dumps({'pregunta': prompt, 'opciones': {chr(65 + index): text for index, text in enumerate(options)}},
                     ensure_ascii=False) + '\nJSON:'
    )
