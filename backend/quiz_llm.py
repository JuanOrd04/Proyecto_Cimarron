import logging
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ollama_client import OllamaError, quiz_client
from quiz_prompts import SISTEMA_EVALUACION, interpretation_prompt, number_prompt
from quiz_concepts import ConceptEvaluator
from quiz_dialogue import assess_open_answer
from quiz_language import feedback_en_espanol


logger = logging.getLogger('QuizLLM')
CLARIFICATION = 'No estoy seguro de haber entendido tu idea. ¿Puedes decirme qué respuesta eliges?'
PARTIAL_FEEDBACK = 'Ya entendí esa parte de tu idea. ¿Qué otra cosa crees que falta para completar tu respuesta?'


class QuizModelUnavailable(RuntimeError):
    pass


class Interpretation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    intent: Literal['answer', 'unknown', 'repeat', 'ambiguous', 'instruction']
    answer: str = Field(max_length=2000)
    option_label: Literal['A', 'B', 'C', 'D'] | None = None


class NumericalAnswer(BaseModel):
    model_config = ConfigDict(extra='forbid')
    number: float | None = Field(allow_inf_nan=False, strict=True)


class OllamaQuizEvaluator:
    def __init__(self, llm=None):
        self.llm = llm or quiz_client
        self.concept_evaluator = ConceptEvaluator(self._request)

    @property
    def model(self):
        return self.llm.model_name

    def _request(self, prompt, schema, timeout=120):
        system = SISTEMA_EVALUACION if 'feedback' in schema.model_fields else None
        text = self.llm.generate(prompt, schema=schema.model_json_schema(), options={
            'temperature': 0, 'num_predict': 250, 'num_ctx': 4096,
        }, timeout=timeout, system=system)
        return schema.model_validate_json(text)

    def _assess(self, question, text, interpretation, grade, previous_turns):
        number = None
        details = {}
        if interpretation.intent in {'repeat', 'ambiguous', 'instruction'} or (
            not interpretation.answer.strip() and interpretation.intent != 'unknown'
        ):
            status, feedback = 'unclear', CLARIFICATION
            if interpretation.intent == 'repeat':
                options = '. '.join(f'{chr(65 + i)}, {option}' for i, option in enumerate(question['options']))
                feedback = f'Claro. {question["prompt"]} Opciones: {options}.'
        elif interpretation.intent == 'unknown':
            status = 'incorrect'
            feedback = f'No pasa nada. La respuesta es {question["answer"]}. {question["explanation"]}'
        elif question['answer'].isdigit():
            number = self._request(number_prompt(question, text), NumericalAnswer).number
            if number is None:
                status, feedback = 'unclear', CLARIFICATION
            else:
                status = 'correct' if number == int(question['answer']) else 'incorrect'
                feedback = ('¡Muy bien! ' if status == 'correct' else f'¡Buen intento! La respuesta es {question["answer"]}. ') + question['explanation']
        else:
            details = self.concept_evaluator.evaluate(question, text, grade, previous_turns)
            status = details['status']
            feedback = details['feedback']
            if status == 'partial':
                recognized = ', '.join(details['matched_concepts'])
                feedback = f'Mencionaste {recognized}. ¿Qué otra idea puedes agregar para completar tu respuesta?' if recognized else PARTIAL_FEEDBACK
            elif status == 'unclear':
                feedback = CLARIFICATION
            elif not feedback:
                feedback = ('¡Muy bien! ' if status == 'correct' else f'¡Buen intento! La respuesta es {question["answer"]}. ') + question['explanation']
        return status, feedback, number, details

    def evaluate(self, question, text, grade, previous_turns=()):
        started = time.monotonic()
        try:
            if question.get('answer_kind'):
                request = lambda prompt, schema: self._request(prompt, schema, timeout=15)
                result = assess_open_answer(request, question, text, grade, previous_turns)
                return {**result, 'source': 'ollama', 'model': self.model,
                        'elapsed_ms': round((time.monotonic() - started) * 1000)}
            interpretation = self._request(interpretation_prompt(text), Interpretation)
            status, feedback, number, details = self._assess(question, text, interpretation, grade, previous_turns)
            feedback = feedback_en_espanol(feedback, status, question['answer'])
        except (OllamaError, ValidationError, ValueError) as exc:
            logger.warning('Evaluación no disponible con %s: %s', self.model, type(exc).__name__)
            raise QuizModelUnavailable('No pude interpretar tu respuesta en este momento. Revisa que Ollama esté abierto y vuelve a intentarlo; tu pregunta sigue pendiente.') from exc

        elapsed_ms = round((time.monotonic() - started) * 1000)
        logger.info('Respuesta interpretada por %s: %s (%s ms)', self.model, status, elapsed_ms)
        return {
            'status': status, 'feedback': feedback, 'interpreted_answer': interpretation.answer,
            'numeric_answer': number, 'source': 'ollama', 'model': self.model, 'elapsed_ms': elapsed_ms,
            **{key: details.get(key, []) for key in ('concepts', 'student_ideas', 'matched_concepts', 'missing_concepts')},
            'concepts_evaluated': details.get('concepts_evaluated', False),
            'initial_assessment': details.get('initial_assessment'),
        }
