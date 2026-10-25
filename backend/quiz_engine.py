"""Dinámicas de primaria con respuestas verificables y sesiones independientes."""

import copy
import random
import threading
import time
import uuid

from quiz_llm import OllamaQuizEvaluator

from quiz_curriculum import SUBJECTS, TOTAL
from quiz_bank import BankQuestionProvider
from quiz_narration import feedback_texts, question_narration


class QuizService:
    def __init__(self, evaluator=None, generator=None):
        self.evaluator = evaluator or OllamaQuizEvaluator()
        self.generator = generator or BankQuestionProvider()
        self.sessions = {}
        self.lock = threading.RLock()

    def _get(self, session_id):
        session = self.sessions.get(session_id)
        if session is None or time.monotonic() - session['updated'] > 7200:
            self.sessions.pop(session_id, None)
            raise KeyError('Esta dinámica terminó o se reinició el servidor. Inicia un juego nuevo.')
        session['updated'] = time.monotonic()
        return session

    def _view(self, session):
        question = session['questions'][session['index']]
        phase = session['phase']
        narration = question_narration(question)
        prepared_audio = {text: question.get('feedback_audio', {}).get(status) for status, text in feedback_texts(question).items()}
        prepared_audio[narration] = question.get('audio')
        response = narration
        if session.get('feedback'):
            response = session['feedback']['text']
        if phase == 'finished':
            response += f' ¡Terminamos! Acertaste {session["score"]} de {TOTAL}.'
        feedback = copy.deepcopy(session.get('feedback'))
        if feedback and 'correct_answer' in feedback and question['answer'] in question['options']:
            feedback['correct_option'] = chr(65 + question['options'].index(question['answer']))
        return {
            'session_id': session['id'], 'grade': session['grade'], 'subject': session['subject'],
            'subject_label': SUBJECTS[session['subject']], 'total': TOTAL, 'answered': len(session['answers']),
            'score': session['score'], 'phase': phase,
            'question': {'id': question['id'], 'prompt': question['prompt'], 'subject': question['subject'], 'options': [{'label': chr(65 + i), 'text': option} for i, option in enumerate(question['options'])],
                         'source': {key: question.get('generation', {}).get(key) for key in ('source_title', 'source_url', 'model')}},
            'feedback': feedback, 'response': response,
            'evaluation': copy.deepcopy(session.get('evaluation')),
            '_prepared_audio': prepared_audio.get(response),
        }

    def prepare(self, grade, subject):
        if grade not in range(1, 7) or subject not in SUBJECTS:
            raise ValueError('Elige un grado y una materia válidos.')
        return self.generator.prepare(grade, subject)

    def start(self, grade, subject):
        if grade not in range(1, 7) or subject not in SUBJECTS:
            raise ValueError('Elige un grado de primero a sexto y una materia válida.')
        rng = random.Random()
        plan = self.generator.plan(subject, rng)
        if getattr(self.generator, 'prepares_rounds', False) is True:
            questions = self.generator.generate_round(grade, subject)
        else:
            questions = [self.generator.generate(grade, plan[0], rng=rng)]
        with self.lock:
            now = time.monotonic()
            self.sessions = {key: value for key, value in self.sessions.items() if now - value['updated'] <= 7200}
            if len(self.sessions) >= 500:
                oldest = min(self.sessions, key=lambda key: self.sessions[key]['updated'])
                del self.sessions[oldest]
            session = {'id': str(uuid.uuid4()), 'grade': grade, 'subject': subject, 'questions': questions, 'plan': plan, 'index': 0, 'score': 0, 'phase': 'question', 'answers': {}, 'feedback': None, 'updated': now, 'turns': [], 'clarifications': {}, 'turn_lock': threading.Lock()}
            self.sessions[session['id']] = session
            if getattr(self.generator, 'prepares_rounds', False) is True:
                self.generator.hold(session['id'])
            result = self._view(session)
            return result

    def answer(self, session_id, question_id, text):
        text = text.strip()
        if not text or len(text) > 2000:
            raise ValueError('Dime tu respuesta con tus propias palabras, en un texto de hasta 2000 caracteres.')
        with self.lock:
            session = self._get(session_id)
            turn_lock = session['turn_lock']
        with turn_lock:
            with self.lock:
                session = self._get(session_id)
                if question_id in session['answers']:
                    return copy.deepcopy(session['answers'][question_id])
                question = session['questions'][session['index']]
                if session['phase'] != 'question' or question['id'] != question_id:
                    raise ValueError('Esa pregunta ya no está activa. Continúa con la pregunta que aparece en pantalla.')
                if text in session['clarifications']:
                    return copy.deepcopy(session['clarifications'][text])
                question = copy.deepcopy(question)
                previous_turns = copy.deepcopy(session['turns'])
                grade = session['grade']
                if getattr(self.generator, 'prepares_rounds', False) is True:
                    self.generator.hold(session_id)

            evaluation = self.evaluator.evaluate(question, text, grade, previous_turns)

            with self.lock:
                session = self._get(session_id)
                if session['questions'][session['index']]['id'] != question_id or session['phase'] != 'question':
                    raise ValueError('Esa pregunta ya no está activa.')
                kind = evaluation['status']
                fields = ('source', 'model', 'status', 'interpreted_answer', 'elapsed_ms', 'numeric_answer',
                          'concepts', 'student_ideas', 'matched_concepts', 'missing_concepts',
                          'concepts_evaluated', 'initial_assessment')
                session['evaluation'] = copy.deepcopy({key: evaluation[key] for key in fields if key in evaluation})
                clarification = kind in {'partial', 'unclear'}
                session['feedback'] = {'correct': None if clarification else kind == 'correct', 'kind': kind, 'text': evaluation['feedback']}
                if clarification:
                    session['turns'].append({'respuesta': text, 'aclaracion': evaluation['feedback']})
                    session['turns'] = session['turns'][-3:]
                    result = self._view(session)
                    session['clarifications'][text] = copy.deepcopy(result)
                    if len(session['clarifications']) > 20:
                        session['clarifications'].pop(next(iter(session['clarifications'])))
                    return result

                session['score'] += int(kind == 'correct')
                session['feedback']['correct_answer'] = question['answer']
                session['phase'] = 'finished' if session['index'] == TOTAL - 1 else 'feedback'
                if session['phase'] == 'finished' and getattr(self.generator, 'prepares_rounds', False) is True:
                    self.generator.release(session_id)
                session['answers'][question_id] = None
                result = self._view(session)
                session['answers'][question_id] = copy.deepcopy(result)
                return result

    def next(self, session_id, question_id):
        with self.lock:
            session = self._get(session_id)
            turn_lock = session['turn_lock']
        with turn_lock:
            with self.lock:
                session = self._get(session_id)
                current = session['questions'][session['index']]
                if current['id'] != question_id and question_id in session['answers']:
                    return self._view(session)
                if session['phase'] == 'finished':
                    return self._view(session)
                if session['phase'] != 'feedback' or current['id'] != question_id:
                    raise ValueError('Responde la pregunta actual antes de continuar.')
                if session['index'] + 1 < len(session['questions']):
                    session['index'] += 1
                    session['phase'] = 'question'
                    session['feedback'] = None
                    session['evaluation'] = None
                    session['turns'] = []
                    session['clarifications'] = {}
                    return self._view(session)
                grade = session['grade']
                subject = session['plan'][session['index'] + 1]
                previous = copy.deepcopy(session['questions'])
            question = self.generator.generate(grade, subject, previous)
            with self.lock:
                session = self._get(session_id)
                session['questions'].append(question)
                session['index'] += 1
                session['phase'] = 'question'
                session['feedback'] = None
                session['evaluation'] = None
                session['turns'] = []
                session['clarifications'] = {}
                return self._view(session)

    def end(self, session_id):
        with self.lock:
            self.sessions.pop(session_id, None)
            if getattr(self.generator, 'prepares_rounds', False) is True:
                self.generator.release(session_id)


quiz_service = QuizService()
