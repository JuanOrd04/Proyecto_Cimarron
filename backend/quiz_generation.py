import logging
import random
import re
import time
import uuid
from fractions import Fraction
import ast
import operator
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ollama_client import OllamaError, quiz_client
from quiz_curriculum import SUBJECTS, TOTAL
from quiz_knowledge import EducationKnowledge
from quiz_llm import QuizModelUnavailable
from quiz_generation_prompts import blind_answer_prompt, generation_prompt


logger = logging.getLogger('QuizGeneration')
MAX_ATTEMPTS = 3
GENERATION_VERSION = 'multiple-choice-v1'


class QuestionDraft(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    pregunta: str = Field(min_length=10, max_length=240)
    respuesta_correcta: str = Field(min_length=1, max_length=60)
    distractores: list[str] = Field(min_length=3, max_length=3)
    explicacion: str = Field(min_length=5, max_length=240)


class MathDraft(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    pregunta: str = Field(min_length=10, max_length=240)
    operacion: str = Field(min_length=3, max_length=60)
    respuesta_correcta: str = Field(min_length=1, max_length=10)
    distractores: list[str] = Field(min_length=3, max_length=3)
    explicacion: str = Field(min_length=5, max_length=240)


class BlindAnswer(BaseModel):
    model_config = ConfigDict(extra='forbid')
    razonamiento: str = Field(max_length=1500)
    eleccion: Literal['A', 'B', 'C', 'D', 'NINGUNA', 'VARIAS']


def arithmetic_value(expression):
    try:
        tree = ast.parse(expression, mode='eval')
    except SyntaxError as exc:
        raise ValueError('Escribe expression como una operación con números y signos, sin signo igual ni unidades.') from exc
    if not isinstance(tree.body, ast.BinOp):
        raise ValueError('Se requiere una operación, no solo el resultado.')
    if len(list(ast.walk(tree))) > 25:
        raise ValueError('Operación demasiado extensa.')
    operations = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}

    def calculate(node):
        if isinstance(node, ast.Constant) and type(node.value) is int and 0 <= node.value <= 10000:
            return Fraction(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            value = operations[type(node.op)](calculate(node.left), calculate(node.right))
            if abs(value) > 1000000:
                raise ValueError('Operación fuera de rango.')
            return value
        raise ValueError('Expresión aritmética no permitida.')

    result = calculate(tree.body)
    if result.denominator != 1 or result < 0:
        raise ValueError('Se requiere un resultado entero no negativo.')
    return str(result.numerator)


def validate_quantities(expression, prompt):
    quantities = [node.value for node in ast.walk(ast.parse(expression, mode='eval')) if isinstance(node, ast.Constant)]
    spoken = [int(value) for value in re.findall(r'(?<!\w)\d+(?!\w)', prompt)]
    if sorted(quantities) != sorted(spoken):
        raise ValueError('La operación debe usar exactamente las cantidades escritas en el problema.')


class OllamaQuestionGenerator:
    def __init__(self, llm=None, knowledge=None):
        self.llm = llm or quiz_client
        self.knowledge = knowledge or EducationKnowledge()

    def plan(self, subject, rng):
        if subject != 'mixto':
            return [subject] * TOTAL
        subjects = [name for name in SUBJECTS if name != 'mixto']
        rng.shuffle(subjects)
        return subjects

    def _request(self, prompt, schema, deadline, temperature=0):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise OllamaError('Se agotó el tiempo de preparación.')
        output_schema = schema.model_json_schema()
        for field in output_schema.get('properties', {}).values():
            field.pop('maxLength', None)
        response = self.llm.generate(prompt, schema=output_schema, options={
            'temperature': temperature, 'num_predict': 300, 'num_ctx': 4096,
        }, timeout=min(25, remaining), priority='background')
        return schema.model_validate_json(response)

    def _check(self, draft, previous):
        """Controles de forma del contenido generado; nunca se aplican a lo que dice el niño."""
        prompt = draft.pregunta
        if '\n' in prompt or re.search(r'(?:^|\s)[a-d][).:]\s', prompt, re.IGNORECASE):
            raise ValueError('Escribe solo la pregunta, sin opciones ni listas.')
        if prompt.count('?') != 1:
            raise ValueError('Escribe una única pregunta con un solo signo de interrogación.')
        if any(prompt.casefold() == question['prompt'].casefold() for question in previous):
            raise ValueError('Plantea una pregunta diferente a las anteriores.')
        options = [draft.respuesta_correcta, *[' '.join(text.split()) for text in draft.distractores]]
        if any(not text or len(text) > 60 or len(text.split()) > 8 for text in options):
            raise ValueError('Las opciones deben ser breves.')
        if len({text.casefold() for text in options}) != 4:
            raise ValueError('Las cuatro opciones deben ser distintas.')
        return options

    def generate(self, grade, subject, previous=(), rng=None):
        rng = rng or random.Random()
        started = time.monotonic()
        deadline = started + 60
        try:
            documents = self.knowledge.retrieve(grade, subject, previous)
        except Exception as exc:
            raise QuizModelUnavailable('La preparación del juego está esperando el material educativo local.') from exc
        if not documents:
            raise QuizModelUnavailable('No se encontró material para esta materia y grado.')
        rng.shuffle(documents)
        reason = ''
        for attempt in range(MAX_ATTEMPTS):
            document = documents[attempt % len(documents)]
            try:
                schema = MathDraft if subject == 'matematicas' else QuestionDraft
                draft = self._request(generation_prompt(grade, subject, document, previous, reason), schema, deadline, 0.5)
                options = self._check(draft, previous)
                answer = draft.respuesta_correcta
                if subject == 'matematicas':
                    answer = arithmetic_value(draft.operacion)
                    validate_quantities(draft.operacion, draft.pregunta)
                    values = [Fraction(text) for text in options]
                    if values[0] != Fraction(answer):
                        raise ValueError(f'La operación {draft.operacion} da {answer}; respuesta_correcta debe coincidir.')
                    if len(set(values)) != 4 or any(value < 0 or value.denominator != 1 for value in values):
                        raise ValueError('Las opciones deben ser cuatro números enteros distintos.')
                    options = [str(value.numerator) for value in values]
                    rng.shuffle(options)
                    review = {'method': 'arithmetic_and_quantities', 'expression': draft.operacion}
                else:
                    if re.search(r'(?<!\w)' + re.escape(answer.casefold()) + r'(?!\w)', draft.pregunta.casefold()):
                        raise ValueError('La pregunta no debe contener su respuesta.')
                    rng.shuffle(options)
                    # Otra consulta responde a ciegas: si no llega sola a la respuesta prevista,
                    # la pregunta es ambigua o tiene más de una opción válida.
                    blind = self._request(blind_answer_prompt(draft.pregunta, options), BlindAnswer, deadline)
                    expected = chr(65 + options.index(answer))
                    if blind.eleccion != expected:
                        raise ValueError('La pregunta fue ambigua o tuvo más de una opción válida; escribe otra más clara.')
                    review = {'method': 'blind_answer', **blind.model_dump()}
                elapsed_ms = round((time.monotonic() - started) * 1000)
                logger.info('Pregunta preparada: %s (%s ms, intento %s)', subject, elapsed_ms, attempt + 1)
                return {
                    'id': str(uuid.uuid4()), 'prompt': draft.pregunta, 'answer': answer,
                    'options': options, 'answer_kind': 'number' if subject == 'matematicas' else 'fact',
                    'explanation': draft.explicacion,
                    'subject': SUBJECTS[subject], 'support': document.page_content,
                    'generation': {
                        'source': 'ollama', 'model': self.llm.model_name, 'version': GENERATION_VERSION,
                        'lesson_id': document.metadata['id'], 'source_title': document.metadata['source_title'],
                        'source_url': document.metadata['source_url'], 'review': review,
                        'expression': review.get('expression'),
                        'attempts': attempt + 1, 'elapsed_ms': elapsed_ms,
                    },
                }
            except (OllamaError, ValidationError, ValueError, ZeroDivisionError) as exc:
                reason = str(exc)[:240]
                logger.info('Preparación descartada: %s', reason)
        raise QuizModelUnavailable('Estoy preparando otra pregunta para esta materia.')
