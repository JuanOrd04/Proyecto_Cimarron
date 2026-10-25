import copy
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import uuid


CACHE_PATH = Path(__file__).parent / 'quiz_cache.sqlite3'


class QuestionCache:
    def __init__(self, namespace, path=CACHE_PATH):
        self.namespace = namespace
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS questions (id TEXT PRIMARY KEY, scope TEXT, payload TEXT, used REAL, created REAL)')
            connection.execute('CREATE INDEX IF NOT EXISTS questions_scope ON questions(scope, used)')

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=3)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _scope(self, grade, subject):
        return f'{self.namespace}:{grade}:{subject}'

    def questions(self, grade, subject):
        with self._connect() as connection:
            rows = connection.execute('SELECT payload FROM questions WHERE scope = ? ORDER BY used, created',
                                      (self._scope(grade, subject),)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def count(self, grade, subject):
        with self._connect() as connection:
            return connection.execute('SELECT COUNT(*) FROM questions WHERE scope = ?',
                                      (self._scope(grade, subject),)).fetchone()[0]

    def add(self, grade, subject, question, audio):
        scope = self._scope(grade, subject)
        key = hashlib.sha256((scope + question['prompt'].strip().casefold()).encode()).hexdigest()
        item = copy.deepcopy(question)
        item['audio'] = audio
        item['generation']['cache_id'] = key
        item['generation']['prepared_at'] = time.time()
        with self._connect() as connection:
            connection.execute('INSERT OR IGNORE INTO questions VALUES (?, ?, ?, ?, ?)',
                               (key, scope, json.dumps(item, ensure_ascii=False), 0, time.time()))

    def take(self, grade, subject, previous=()):
        excluded = {question.get('generation', {}).get('cache_id') for question in previous}
        used_lessons = {question.get('generation', {}).get('lesson_id') for question in previous}
        questions = self.questions(grade, subject)
        questions.sort(key=lambda question: question['generation'].get('lesson_id') in used_lessons)
        for question in questions:
            key = question['generation']['cache_id']
            if key in excluded:
                continue
            with self._connect() as connection:
                connection.execute('UPDATE questions SET used = ? WHERE id = ?', (time.time(), key))
            question['id'] = str(uuid.uuid4())
            question['generation']['delivery'] = 'prepared'
            return question
        return None
