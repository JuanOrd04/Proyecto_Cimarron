"""Banco de preguntas revisado por docentes; el LLM solo interpreta lo que responde el niño."""

import copy
from contextlib import contextmanager
import hashlib
import json
import logging
from pathlib import Path
import random
import sqlite3
import threading
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator

from quiz_curriculum import SUBJECTS, TOTAL
from quiz_narration import feedback_texts, question_narration


logger = logging.getLogger('QuizBank')
BANK_PATH = Path(__file__).parent / 'data' / 'banco_preguntas.json'
AUDIO_PATH = Path(__file__).parent / 'quiz_audio.sqlite3'


class BankQuestion(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    id: str = Field(min_length=1)
    subject: str
    min_grade: int = Field(ge=1, le=6)
    max_grade: int = Field(ge=1, le=6)
    prompt: str = Field(min_length=5, max_length=240)
    answer: str = Field(min_length=1, max_length=80)
    distractors: list[str] = Field(min_length=3, max_length=3)
    explanation: str = Field(min_length=5, max_length=300)

    @model_validator(mode='after')
    def valid_question(self):
        if self.subject not in SUBJECTS or self.subject == 'mixto' or self.min_grade > self.max_grade:
            raise ValueError(f'{self.id}: materia o grados inválidos.')
        if len({text.casefold() for text in [self.answer, *self.distractors]}) != 4:
            raise ValueError(f'{self.id}: las cuatro opciones deben ser distintas.')
        return self


def load_bank(path=BANK_PATH):
    rows = [BankQuestion.model_validate(row) for row in json.loads(Path(path).read_text(encoding='utf-8'))]
    if len({row.id for row in rows}) != len(rows):
        raise ValueError('El banco de preguntas tiene identificadores repetidos.')
    return rows


def to_question(row):
    options = [row.answer, *row.distractors]
    # El orden depende del id: es estable entre partidas y su narración puede prepararse una vez.
    random.Random(row.id).shuffle(options)
    return {
        'id': row.id, 'bank_id': row.id, 'prompt': row.prompt, 'answer': row.answer, 'options': options,
        'answer_kind': 'number' if row.answer.isdigit() else 'fact', 'explanation': row.explanation,
        'subject': SUBJECTS[row.subject], 'support': row.explanation, 'generation': {'source': 'bank'},
        'grades': [row.min_grade, row.max_grade],
    }


def spoken_texts(question):
    return [question_narration(question), *feedback_texts(question).values()]


class AudioCache:
    def __init__(self, path=AUDIO_PATH):
        self.path = Path(path)
        with self._connect() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS audio (key TEXT PRIMARY KEY, wav TEXT)')

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=3)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def key(text):
        voice = (Path(__file__).parent / 'tts_engine.py').read_bytes()
        return hashlib.sha256(voice + text.encode()).hexdigest()

    def get(self, text):
        with self._connect() as connection:
            row = connection.execute('SELECT wav FROM audio WHERE key = ?', (self.key(text),)).fetchone()
        return row[0] if row else None

    def put(self, text, wav):
        with self._connect() as connection:
            connection.execute('INSERT OR REPLACE INTO audio VALUES (?, ?)', (self.key(text), wav))


def synthesize(text):
    from tts_engine import tts_service
    return tts_service.synthesize_to_base64_wav(text)


class BankQuestionProvider:
    prepares_rounds = True

    def __init__(self, bank=None, audio=None, synthesize=synthesize):
        self.questions = [to_question(row) for row in (bank if bank is not None else load_bank())]
        self.audio = audio or AudioCache()
        self.synthesize = synthesize
        self.worker = None
        self.closed = False

    def _pool(self, grade, subject):
        return [q for q in self.questions
                if q['subject'] == SUBJECTS[subject] and q['grades'][0] <= grade <= q['grades'][1]]

    def plan(self, subject, rng):
        if subject != 'mixto':
            return [subject] * TOTAL
        subjects = [name for name in SUBJECTS if name != 'mixto']
        rng.shuffle(subjects)
        return subjects

    def status(self, grade, subject):
        subjects = [name for name in SUBJECTS if name != 'mixto'] if subject == 'mixto' else [subject]
        counts = {name: len(self._pool(grade, name)) for name in subjects}
        ready = min(TOTAL, sum(counts.values()))
        return {'state': 'ready' if ready >= TOTAL else 'unavailable', 'ready': ready, 'required': TOTAL, 'subjects': counts}

    def prepare(self, grade, subject):
        return self.status(grade, subject)

    def generate_round(self, grade, subject, rng=None):
        rng = rng or random.Random()
        chosen = []
        for name in self.plan(subject, rng):
            pool = [q for q in self._pool(grade, name) if q not in chosen]
            if pool:
                chosen.append(rng.choice(pool))
        if len(chosen) < TOTAL:
            raise ValueError('El banco no tiene suficientes preguntas para ese grado y materia.')
        round_questions = []
        for question in chosen[:TOTAL]:
            item = copy.deepcopy(question)
            item['id'] = str(uuid.uuid4())
            item['audio'] = self.audio.get(question_narration(item))
            item['feedback_audio'] = {status: self.audio.get(text) for status, text in feedback_texts(item).items()}
            round_questions.append(item)
        return round_questions

    def hold(self, session_id):
        pass

    def release(self, session_id):
        pass

    def warm_audio(self):
        """Sintetiza en segundo plano las voces del banco que aún no están guardadas."""
        if self.worker is None:
            self.worker = threading.Thread(target=self._warm, name='quiz-audio', daemon=True)
            self.worker.start()

    def _warm(self):
        pending = [text for question in self.questions for text in spoken_texts(question)]
        for text in pending:
            if self.closed:
                return
            if self.audio.get(text):
                continue
            try:
                wav = self.synthesize(text)
                if wav:
                    self.audio.put(text, wav)
            except Exception as exc:
                logger.warning('No se pudo preparar una voz del banco: %s', type(exc).__name__)
        logger.info('Voces del banco de preguntas listas.')

    def close(self):
        self.closed = True
