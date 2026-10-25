"""Control local del idioma de la retroalimentación, independiente de la calificación."""

from functools import lru_cache

from langid.langid import LanguageIdentifier, model


@lru_cache(maxsize=1)
def detector_idioma():
    detector = LanguageIdentifier.from_modelstring(model)
    detector.set_languages(['es', 'en'])
    return detector


def feedback_en_espanol(texto, estado, referencia):
    texto = texto.strip()
    if texto and detector_idioma().classify(texto)[0] == 'es':
        return texto
    mensajes = {
        'correct': '¡Muy bien! Tu respuesta es correcta.',
        'incorrect': f'Buen intento. Una respuesta es {referencia}.',
        'partial': 'Vas por buen camino. ¿Puedes completar lo que pide la pregunta?',
        'unclear': '¿Puedes decirme con otras palabras qué respuesta eliges?',
    }
    return mensajes[estado]
