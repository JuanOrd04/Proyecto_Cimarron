import tempfile
import json
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

from inference_queue import InferenceQueue
from quiz_cache import QuestionCache
from quiz_engine import QuizService
from quiz_generation import OllamaQuestionGenerator
from quiz_narration import feedback_texts
from quiz_preparation import PreparedQuestionGenerator, QuizPreparing


def question(index, subject='Biología', lesson=None):
    return {'id': str(index), 'prompt': f'Pregunta de prueba número {index}', 'answer': 'Dato de prueba',
            'options': [], 'answer_kind': 'fact', 'explanation': 'Explicación de prueba.', 'subject': subject,
            'support': 'Contenido de prueba.', 'generation': {'source': 'ollama', 'model': 'gemma2:2b',
                'lesson_id': lesson or str(index), 'source_title': 'Prueba', 'source_url': 'https://example.org'}}


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'questions.sqlite3'
        self.cache = QuestionCache('test-v1', self.path)
        self.generator = Mock()
        self.generator.plan.side_effect = OllamaQuestionGenerator().plan
        self.prepared = PreparedQuestionGenerator(self.generator, self.cache, synthesize=lambda text: 'wav-test')

    def tearDown(self):
        self.prepared.close()
        if self.prepared.worker:
            self.prepared.worker.join(timeout=2)
        self.temp.cleanup()

    def add(self, index, grade=2, subject='biologia', lesson=None):
        self.cache.add(grade, subject, question(index, lesson=lesson), 'wav-test')

    def test_cache_survives_restart_but_never_crosses_versions_grades_or_subjects(self):
        self.add(1)
        restarted = QuestionCache('test-v1', self.path)
        self.assertEqual(restarted.count(2, 'biologia'), 1)
        self.assertEqual(restarted.take(2, 'biologia')['audio'], 'wav-test')
        self.assertEqual(restarted.count(1, 'biologia'), 0)
        self.assertEqual(restarted.count(2, 'espanol'), 0)
        self.assertEqual(QuestionCache('test-v2', self.path).count(2, 'biologia'), 0)

    def test_duplicate_questions_do_not_fill_readiness_and_round_has_five_unique_ids(self):
        self.add(1)
        self.add(1)
        self.assertEqual(self.cache.count(2, 'biologia'), 1)
        self.assertEqual(self.prepared.status(2, 'biologia')['state'], 'preparing')
        for index in range(2, 6):
            self.add(index)
        self.prepared.prepare = Mock(return_value=self.prepared.status(2, 'biologia'))
        questions = self.prepared.generate_round(2, 'biologia')
        self.assertEqual(len({q['prompt'] for q in questions}), 5)
        self.assertEqual(len({q['id'] for q in questions}), 5)
        self.generator.generate.assert_not_called()

    def test_new_lessons_are_preferred_before_repeating_a_lesson(self):
        self.add(1, lesson='one')
        self.add(2, lesson='one')
        self.add(3, lesson='two')
        first = self.cache.take(2, 'biologia')
        second = self.cache.take(2, 'biologia', [first])
        self.assertNotEqual(first['generation']['lesson_id'], second['generation']['lesson_id'])

    def test_unprepared_round_never_creates_an_empty_session(self):
        self.prepared.prepare = Mock(return_value=self.prepared.status(2, 'biologia'))
        service = QuizService(evaluator=Mock(), generator=self.prepared)
        with self.assertRaises(QuizPreparing):
            service.start(2, 'biologia')
        self.assertEqual(service.sessions, {})

    def test_prepared_full_round_never_calls_generation_or_voice_on_next(self):
        for index in range(5):
            self.add(index)
        self.prepared.prepare = Mock(return_value=self.prepared.status(2, 'biologia'))
        evaluator = Mock()
        evaluator.evaluate.return_value = {'status': 'correct', 'feedback': 'Muy bien.', 'source': 'ollama'}
        service = QuizService(evaluator, self.prepared)
        game = service.start(2, 'biologia')
        for index in range(5):
            self.assertEqual(game['_prepared_audio'], 'wav-test')
            self.assertNotIn('answer', game['question'])
            qid = game['question']['id']
            response = service.answer(game['session_id'], qid, 'Mi respuesta')
            if index < 4:
                game = service.next(game['session_id'], qid)
                self.assertEqual(service.next(game['session_id'], qid), game)
        self.assertEqual(response['phase'], 'finished')
        self.assertEqual(response['score'], 5)
        self.assertFalse(self.prepared.active_rounds)
        self.generator.generate.assert_not_called()

    def test_active_round_pauses_background_work_and_expired_rounds_do_not_block_it(self):
        self.prepared.targets[(2, 'biologia')] = (2, time.monotonic())
        self.prepared.hold('participant')
        with self.prepared.condition:
            self.assertIsNone(self.prepared._next())
        self.prepared.release('participant')
        with self.prepared.condition:
            self.assertEqual(self.prepared._next(), (2, 'biologia'))
            self.prepared.active_rounds['abandoned'] = time.monotonic() - 1
            self.assertEqual(self.prepared._next(), (2, 'biologia'))

    def test_newest_unready_profile_is_completed_before_other_grades(self):
        for grade in (2, 1):
            self.prepared.prepare(grade, 'mixto')
        self.prepared.close()
        for index, name in enumerate(['matematicas', 'ciencias_naturales', 'biologia', 'espanol']):
            self.add(index, grade=1, subject=name)
        with self.prepared.condition:
            self.prepared.failures[(1, 'geografia')] = 1
            self.prepared.retry_at[(1, 'geografia')] = time.monotonic() + 60
            self.assertEqual(self.prepared._next()[0], 1)

    def test_four_option_round_reuses_full_narration_and_reveals_solution_only_after_grading(self):
        fixtures = json.loads((Path(__file__).parent / 'fixtures' / 'semantic_questions.json').read_text())
        for index, fixture in enumerate(fixtures):
            self.cache.add(2, 'biologia', {**question(index), **fixture}, 'wav-test')
        self.prepared.prepare = Mock(return_value=self.prepared.status(2, 'biologia'))
        evaluator = Mock()
        evaluator.evaluate.return_value = {'status': 'correct', 'feedback': 'Muy bien.'}
        service = QuizService(evaluator, self.prepared)
        game = service.start(2, 'biologia')
        self.assertEqual(game['_prepared_audio'], 'wav-test')
        self.assertEqual(len(game['question']['options']), 4)
        self.assertNotIn('correct_option', game['question'])
        for option in game['question']['options']:
            self.assertIn(f'{option["label"]}: {option["text"]}', game['response'])
        response = service.answer(game['session_id'], game['question']['id'], fixtures[0]['answer'])
        expected = next(option['label'] for option in game['question']['options'] if option['text'] == fixtures[0]['answer'])
        self.assertEqual(response['feedback']['correct_option'], expected)
        following = service.next(game['session_id'], game['question']['id'])
        self.assertEqual(following['_prepared_audio'], 'wav-test')

    def test_mixed_round_requires_variety_instead_of_five_questions_from_one_subject(self):
        for index in range(5):
            self.add(index)
        status = self.prepared.status(2, 'mixto')
        self.assertEqual(status['ready'], 4)
        self.assertEqual(status['state'], 'preparing')

    def test_mixed_round_can_use_other_prepared_subjects_when_one_is_unavailable(self):
        for index in range(2):
            self.add(index, subject='biologia')
            self.add(index + 2, subject='matematicas')
        self.add(4, subject='geografia')
        with self.prepared.condition:
            self.prepared.failures[(2, 'espanol')] = 3
        status = self.prepared.status(2, 'mixto')
        self.assertEqual(status['state'], 'ready')
        self.prepared.prepare = Mock(return_value=status)
        questions = self.prepared.generate_round(2, 'mixto')
        self.assertEqual(len(questions), 5)
        self.assertEqual(len({q['prompt'] for q in questions}), 5)
        self.generator.generate.assert_not_called()

    def test_worker_prepares_audio_before_marking_question_ready(self):
        counter = iter(range(20))
        self.generator.generate.side_effect = lambda *args, **kwargs: question(next(counter))
        self.prepared.prepare(2, 'biologia')
        deadline = time.monotonic() + 2
        with self.prepared.condition:
            while self.prepared.status(2, 'biologia')['state'] != 'ready' and time.monotonic() < deadline:
                self.prepared.condition.wait(.01)
        self.assertEqual(self.prepared.status(2, 'biologia')['state'], 'ready')
        self.assertTrue(all(q['audio'] == 'wav-test' for q in self.cache.questions(2, 'biologia')))
        self.assertTrue(all(q['feedback_audio'] == {'correct': 'wav-test', 'incorrect': 'wav-test'}
                            for q in self.cache.questions(2, 'biologia')))

    def test_graded_feedback_reuses_its_prepared_voice(self):
        for index in range(5):
            item = question(index)
            item['feedback_audio'] = {'correct': 'wav-correct', 'incorrect': 'wav-incorrect'}
            self.cache.add(2, 'biologia', item, 'wav-test')
        self.prepared.prepare = Mock(return_value=self.prepared.status(2, 'biologia'))
        evaluator = Mock()
        service = QuizService(evaluator, self.prepared)
        game = service.start(2, 'biologia')
        current = service.sessions[game['session_id']]['questions'][0]
        evaluator.evaluate.return_value = {'status': 'incorrect', 'feedback': feedback_texts(current)['incorrect']}
        response = service.answer(game['session_id'], game['question']['id'], 'Mi respuesta')
        self.assertEqual(response['_prepared_audio'], 'wav-incorrect')

    def test_failure_is_visible_and_does_not_spin_or_insert_a_fake_question(self):
        self.generator.generate.side_effect = RuntimeError('Modelo apagado')
        self.prepared.prepare(2, 'biologia')
        deadline = time.monotonic() + 2
        while not self.prepared.failures and time.monotonic() < deadline:
            threading.Event().wait(.005)
        self.assertEqual(self.generator.generate.call_count, 1)
        self.assertEqual(self.cache.count(2, 'biologia'), 0)
        with self.prepared.condition:
            self.prepared.failures[(2, 'biologia')] = 3
        self.assertEqual(self.prepared.status(2, 'biologia')['state'], 'unavailable')


class InferenceQueueTests(unittest.TestCase):
    def test_interactive_request_precedes_waiting_background_job(self):
        queue = InferenceQueue()
        acquired = []
        background_started, interactive_started = threading.Event(), threading.Event()

        def work(priority, started):
            started.set()
            with queue.acquire(priority, 2):
                acquired.append(priority)

        with queue.acquire('interactive', 2):
            bg = threading.Thread(target=work, args=('background', background_started))
            fg = threading.Thread(target=work, args=('interactive', interactive_started))
            bg.start()
            self.assertTrue(background_started.wait(1))
            fg.start()
            self.assertTrue(interactive_started.wait(1))
            deadline = time.monotonic() + 1
            while queue.esperas_interactivas == 0 and time.monotonic() < deadline:
                threading.Event().wait(.001)
        fg.join(2)
        bg.join(2)
        self.assertEqual(acquired, ['interactive', 'background'])

    def test_timeout_and_exception_do_not_lock_out_later_requests(self):
        queue = InferenceQueue()
        errors = []

        def wait_for_busy_queue():
            try:
                with queue.acquire('interactive', .01):
                    self.fail('Debió agotar su tiempo en la cola.')
            except TimeoutError:
                errors.append('timeout')

        with queue.acquire('interactive', 1):
            waiter = threading.Thread(target=wait_for_busy_queue)
            waiter.start()
            waiter.join(1)
        self.assertEqual(errors, ['timeout'])
        self.assertEqual(queue.esperas_interactivas, 0)
        with self.assertRaises(ValueError):
            with queue.acquire('interactive', 1):
                raise ValueError('Error de inferencia')
        with queue.acquire('interactive', 1) as remaining:
            self.assertGreater(remaining, 0)


if __name__ == '__main__':
    unittest.main()
