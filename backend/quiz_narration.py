def question_narration(question):
    options = question.get('options', [])
    if not options:
        return question['prompt']
    choices = '. '.join(f'{chr(65 + index)}: {text}' for index, text in enumerate(options))
    return f'{question["prompt"]} {choices}.'


def hint_text(question):
    return f'Te doy una pista: {question["hint"]} ¿Cuál opción eliges?'


def feedback_texts(question):
    """Retroalimentación de cada resultado; se fija al preparar la pregunta para sintetizar su voz con anticipación."""
    explanation = question['explanation']
    return {
        'correct': f'¡Muy bien! {explanation}',
        'incorrect': f'Buen intento. La respuesta es {question["answer"]}. {explanation}',
    }
