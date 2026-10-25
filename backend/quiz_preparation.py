from collections import OrderedDict
import hashlib
import logging
from pathlib import Path
import random
import threading
import time

from ollama_client import QUIZ_MODEL_NAME
from quiz_cache import QuestionCache
from quiz_curriculum import SUBJECTS
from quiz_generation import GENERATION_VERSION, OllamaQuestionGenerator
from quiz_knowledge import DATA_PATH
from quiz_narration import feedback_texts, question_narration


logger = logging.getLogger('QuizPreparation')


class QuizPreparing(RuntimeError):
    pass


def cache_namespace():
    root = Path(__file__).parent
    # Solo lo que cambia el contenido preparado; ajustar la evaluación no obliga a regenerar preguntas.
    content = QUIZ_MODEL_NAME.encode() + GENERATION_VERSION.encode()
    for path in (DATA_PATH, root / 'quiz_generation.py', root / 'quiz_generation_prompts.py', root / 'quiz_narration.py', root / 'tts_engine.py'):
        content += path.read_bytes()
    return hashlib.sha256(content).hexdigest()[:20]


def profile_subjects(subject):
    return [name for name in SUBJECTS if name != 'mixto'] if subject == 'mixto' else [subject]


def synthesize_question(text):
    from tts_engine import tts_service
    return tts_service.synthesize_to_base64_wav(text)


class PreparedQuestionGenerator:
    prepares_rounds = True

    def __init__(self, generator=None, cache=None, synthesize=None):
        self.generator = generator or OllamaQuestionGenerator()
        self.cache = cache or QuestionCache(cache_namespace())
        self.synthesize = synthesize or synthesize_question
        self.condition = threading.Condition()
        self.targets = OrderedDict()
        self.profiles = OrderedDict()
        self.retry_at = {}
        self.failures = {}
        self.active_rounds = {}
        self.worker = None
        self.closed = False

    def plan(self, subject, rng):
        plan = self.generator.plan(subject, rng)
        return plan

    def prepare(self, grade, subject):
        subjects = profile_subjects(subject)
        target = 2 if subject == 'mixto' else 6
        with self.condition:
            now = time.monotonic()
            self.profiles[(grade, subject)] = now
            self.profiles.move_to_end((grade, subject), last=False)
            for name in reversed(subjects):
                key = (grade, name)
                self.failures.pop(key, None)
                self.retry_at.pop(key, None)
                self.targets[key] = (max(target, self.targets.get(key, (0, 0))[0]), now)
                self.targets.move_to_end(key, last=False)
            if self.worker is None:
                self.worker = threading.Thread(target=self._run, name='quiz-preparation', daemon=True)
                self.worker.start()
            self.condition.notify_all()
        return self.status(grade, subject)

    def status(self, grade, subject):
        subjects = profile_subjects(subject)
        counts = {name: self.cache.count(grade, name) for name in subjects}
        with self.condition:
            if subject == 'mixto':
                variety = sum(bool(count) for count in counts.values())
                ready = min(5 if variety >= 2 else 4, sum(counts.values()))
                potential = [max(count, 2 if self.failures.get((grade, name), 0) < 3 else 0) for name, count in counts.items()]
                unavailable = sum(potential) < 5 or sum(bool(count) for count in potential) < 2
            else:
                ready = min(5, counts[subject])
                unavailable = self.failures.get((grade, subject), 0) >= 3
        state = 'ready' if ready >= 5 else 'unavailable' if unavailable else 'preparing'
        return {'state': state, 'ready': ready, 'required': 5, 'subjects': counts}

    def generate_round(self, grade, subject):
        status = self.prepare(grade, subject)
        if status['state'] != 'ready':
            raise QuizPreparing('Estoy preparando las cinco preguntas y sus voces.')
        plan = self.generator.plan(subject, random.Random())
        questions = []
        while len(questions) < 5:
            before = len(questions)
            for name in plan:
                question = self.cache.take(grade, name, questions)
                if question is not None:
                    questions.append(question)
                    if len(questions) == 5:
                        break
            if len(questions) == before:
                raise QuizPreparing('Estoy terminando de preparar el juego.')
        return questions

    def generate(self, grade, subject, previous=(), rng=None):
        question = self.cache.take(grade, subject, previous)
        self.prepare(grade, subject)
        if question is None:
            raise QuizPreparing('Estoy preparando tu próxima pregunta.')
        return question

    def hold(self, session_id):
        with self.condition:
            self.active_rounds[session_id] = time.monotonic() + 300

    def release(self, session_id):
        with self.condition:
            self.active_rounds.pop(session_id, None)
            self.condition.notify_all()

    def _next(self):
        now = time.monotonic()
        self.active_rounds = {key: expiry for key, expiry in self.active_rounds.items() if expiry > now}
        if self.active_rounds:
            return None
        for key, (target, requested) in list(self.targets.items()):
            if now - requested > 600:
                del self.targets[key]
        self.profiles = OrderedDict((profile, requested) for profile, requested in self.profiles.items() if now - requested <= 600)
        # Primero se completa el perfil pedido más recientemente que todavía no puede jugarse;
        # así una materia que falla no hace esperar a ese grado mientras se preparan otros.
        pending = next(([(grade, name) for name in profile_subjects(subject)] for grade, subject in self.profiles
                        if self.status(grade, subject)['state'] == 'preparing'), [])
        pending.sort(key=lambda key: self.cache.count(*key))
        for keys in (pending, list(self.targets)):
            for key in keys:
                if key not in self.targets or self.retry_at.get(key, 0) > now or self.failures.get(key, 0) >= 3:
                    continue
                if self.cache.count(*key) < self.targets[key][0]:
                    self.targets.move_to_end(key)
                    return key
        return None

    def _run(self):
        while True:
            with self.condition:
                if self.closed:
                    return
                key = self._next()
                if key is None:
                    self.condition.wait(1)
                    continue
            try:
                previous = self.cache.questions(*key)
                question = self.generator.generate(*key, previous=previous)
                audio = self.synthesize(question_narration(question))
                question['feedback_audio'] = {status: self.synthesize(text) for status, text in feedback_texts(question).items()}
                if not audio or not all(question['feedback_audio'].values()):
                    raise RuntimeError('No se pudo preparar la voz.')
                if not self.closed:
                    self.cache.add(*key, question, audio)
                    with self.condition:
                        self.failures.pop(key, None)
                    logger.info('Pregunta y audio listos para %s', key)
            except Exception as exc:
                logger.warning('La preparación continuará: %s', type(exc).__name__)
                with self.condition:
                    self.failures[key] = self.failures.get(key, 0) + 1
                    self.retry_at[key] = time.monotonic() + 5

    def close(self):
        with self.condition:
            self.closed = True
            self.condition.notify_all()
