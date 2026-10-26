import concurrent.futures
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock

from quiz_bank import AudioCache, BankQuestionProvider
from quiz_engine import QuizService, SUBJECTS
from quiz_llm import QuizModelUnavailable


def result(status, text='Una explicación para el niño.'):
    return {'status': status, 'feedback': text, 'interpreted_answer': 'Idea interpretada', 'numeric_answer': None,
            'source': 'ollama', 'model': 'test-model', 'elapsed_ms': 1}


class QuizTests(unittest.TestCase):
    def setUp(self):
        self.evaluator = Mock()
        self.evaluator.evaluate.side_effect = lambda q, text, grade, turns, context=None: result(
            'correct' if text == q['answer'] else 'incorrect', f"La respuesta es {q['answer']}. {q['explanation']}")
        self.temp = tempfile.TemporaryDirectory()
        self.generator = BankQuestionProvider(audio=AudioCache(Path(self.temp.name) / 'audio.sqlite3'), synthesize=None)
        self.service = QuizService(self.evaluator, self.generator)

    def tearDown(self):
        self.temp.cleanup()

    def test_five_questions_for_every_grade_and_subject(self):
        for grade in range(1, 7):
            for subject in SUBJECTS:
                with self.subTest(grade=grade, subject=subject):
                    game = self.service.start(grade, subject)
                    ids = set()
                    for index in range(5):
                        qid = game['question']['id']
                        ids.add(qid)
                        self.assertNotIn('answer', game['question'])
                        self.assertEqual(len({option['text'] for option in game['question']['options']}), 4)
                        expected = self.service.sessions[game['session_id']]['questions'][index]['answer']
                        response = self.service.answer(game['session_id'], qid, expected)
                        self.assertEqual(response['score'], index + 1)
                        self.assertEqual(response['answered'], index + 1)
                        self.assertEqual(response['evaluation']['source'], 'ollama')
                        if index < 4:
                            game = self.service.next(game['session_id'], qid)
                    self.assertEqual(response['phase'], 'finished')
                    self.assertEqual(response['score'], 5)
                    self.assertEqual(len(ids), 5)

    def test_unavailable_bank_round_does_not_create_an_empty_session(self):
        self.generator.generate_round = Mock(side_effect=ValueError('Sin preguntas'))
        with self.assertRaises(ValueError):
            self.service.start(2, 'biologia')
        self.assertEqual(self.service.sessions, {})

    def test_free_long_answer_is_sent_intact_to_model_and_uses_its_feedback(self):
        game = self.service.start(2, 'biologia')
        answer = 'Pues yo creo que hay que regarla y ponerla donde le llegue la luz del sol. ' * 8
        self.evaluator.evaluate.side_effect = None
        self.evaluator.evaluate.return_value = result('correct', '¡Muy bien! Mencionaste el agua y la luz.')
        response = self.service.answer(game['session_id'], game['question']['id'], answer)
        self.assertEqual(self.evaluator.evaluate.call_args.args[1], answer.strip())
        self.assertTrue(response['feedback']['correct'])
        self.assertEqual(response['feedback']['text'], '¡Muy bien! Mencionaste el agua y la luz.')

    def test_clarification_preserves_turn_and_combines_followup(self):
        game = self.service.start(2, 'biologia')
        qid = game['question']['id']
        self.evaluator.evaluate.side_effect = [result('partial', '¿Qué más necesita?'), result('correct')]
        partial = self.service.answer(game['session_id'], qid, 'Agua')
        self.assertEqual(partial['phase'], 'question')
        self.assertEqual(partial['answered'], 0)
        self.assertEqual(partial['score'], 0)
        self.assertIsNone(partial['feedback']['correct'])
        self.assertNotIn('correct_answer', partial['feedback'])
        self.assertEqual(partial['response'], '¿Qué más necesita?')
        self.assertEqual(self.service.answer(game['session_id'], qid, 'Agua'), partial)
        with self.assertRaises(ValueError):
            self.service.next(game['session_id'], qid)
        completed = self.service.answer(game['session_id'], qid, 'Y también luz')
        self.assertEqual(completed['score'], 1)
        self.assertEqual(self.evaluator.evaluate.call_args.args[3], [{'respuesta': 'Agua', 'aclaracion': '¿Qué más necesita?'}])
        following = self.service.next(game['session_id'], qid)
        self.assertIsNone(following['feedback'])
        self.assertIsNone(following['evaluation'])
        self.assertEqual(self.service.sessions[game['session_id']]['turns'], [])

    def test_concepts_reach_api_view_without_exposing_solution_in_feedback(self):
        game = self.service.start(2, 'biologia')
        self.evaluator.evaluate.side_effect = None
        evaluation = {**result('partial', 'Mencionaste agua. ¿Qué otra cosa falta?'),
                      'concepts': [{'name': 'Agua', 'state': 'recognized'}, {'name': 'Luz', 'state': 'missing'}],
                      'matched_concepts': ['Agua'], 'missing_concepts': ['Luz'], 'concepts_evaluated': True}
        self.evaluator.evaluate.return_value = evaluation
        response = self.service.answer(game['session_id'], game['question']['id'], 'Creo que agua')
        self.assertEqual(response['evaluation']['matched_concepts'], ['Agua'])
        self.assertEqual(response['evaluation']['missing_concepts'], ['Luz'])
        self.assertEqual(response['phase'], 'question')
        self.assertEqual(response['score'], 0)
        self.assertEqual(response['answered'], 0)
        self.assertNotIn('correct_answer', response['feedback'])
        response['evaluation']['concepts'][0]['name'] = 'Modificado'
        evaluation['concepts'][0]['name'] = 'Otro'
        retry = self.service.answer(game['session_id'], game['question']['id'], 'Creo que agua')
        self.assertEqual(retry['evaluation']['concepts'][0]['name'], 'Agua')

    def test_wrong_answer_gives_explanation_without_a_point(self):
        game = self.service.start(2, 'biologia')
        question = self.service.sessions[game['session_id']]['questions'][0]
        wrong = next(option for option in question['options'] if option != question['answer'])
        response = self.service.answer(game['session_id'], question['id'], wrong)
        self.assertFalse(response['feedback']['correct'])
        self.assertEqual(response['score'], 0)
        self.assertIn(question['answer'], response['feedback']['text'])

    def test_retries_do_not_count_or_skip_twice(self):
        game = self.service.start(3, 'matematicas')
        question = self.service.sessions[game['session_id']]['questions'][0]
        response = self.service.answer(game['session_id'], question['id'], question['answer'])
        self.assertEqual(self.service.answer(game['session_id'], question['id'], question['answer']), response)
        self.assertEqual(self.evaluator.evaluate.call_count, 1)
        following = self.service.next(game['session_id'], question['id'])
        self.assertEqual(self.service.next(game['session_id'], question['id']), following)
        self.assertEqual(following['answered'], 1)

    def test_failure_does_not_silently_fall_back_to_text_matching(self):
        game = self.service.start(4, 'geografia')
        question = self.service.sessions[game['session_id']]['questions'][0]
        self.evaluator.evaluate.side_effect = QuizModelUnavailable('Ollama no está disponible')
        with self.assertRaises(QuizModelUnavailable):
            self.service.answer(game['session_id'], question['id'], question['answer'])
        session = self.service.sessions[game['session_id']]
        self.assertEqual(session['phase'], 'question')
        self.assertEqual(session['score'], 0)
        self.assertFalse(session['answers'])
        self.assertIsNone(session['feedback'])

    def test_concurrent_retry_evaluates_once_without_blocking_other_participant(self):
        first = self.service.start(1, 'matematicas')
        second = self.service.start(6, 'espanol')
        started, release = threading.Event(), threading.Event()
        first_id = first['question']['id']
        def evaluate(q, text, grade, turns, context=None):
            if q['id'] == first_id:
                started.set()
                if not release.wait(5):
                    raise RuntimeError('La segunda sesión quedó bloqueada')
            return result('correct')
        self.evaluator.evaluate.side_effect = evaluate
        with concurrent.futures.ThreadPoolExecutor(3) as pool:
            pending = pool.submit(self.service.answer, first['session_id'], first_id, 'Uno')
            self.assertTrue(started.wait(2))
            retry = pool.submit(self.service.answer, first['session_id'], first_id, 'Uno')
            try:
                other = pool.submit(self.service.answer, second['session_id'], second['question']['id'], 'Ella').result(timeout=2)
                self.assertEqual(other['score'], 1)
            finally:
                release.set()
            self.assertEqual(pending.result(), retry.result())
        self.assertEqual(self.evaluator.evaluate.call_count, 2)

    def test_empty_or_excessive_answer_and_premature_next_preserve_question(self):
        game = self.service.start(4, 'geografia')
        for text in ['   ', 'x' * 2001]:
            with self.assertRaises(ValueError):
                self.service.answer(game['session_id'], game['question']['id'], text)
        with self.assertRaises(ValueError):
            self.service.next(game['session_id'], game['question']['id'])
        self.evaluator.evaluate.assert_not_called()

    def test_ending_during_evaluation_does_not_restore_session_or_award_points(self):
        game = self.service.start(2, 'biologia')
        def evaluate(*args):
            self.service.end(game['session_id'])
            return result('correct')
        self.evaluator.evaluate.side_effect = evaluate
        with self.assertRaises(KeyError):
            self.service.answer(game['session_id'], game['question']['id'], 'Mi respuesta')
        self.assertNotIn(game['session_id'], self.service.sessions)

    def test_participants_and_clarification_context_are_separate(self):
        first = self.service.start(1, 'matematicas')
        second = self.service.start(6, 'espanol')
        self.evaluator.evaluate.side_effect = [result('unclear'), result('correct')]
        self.service.answer(first['session_id'], first['question']['id'], 'No escuché la pregunta')
        self.service.answer(second['session_id'], second['question']['id'], 'Creo que es ella')
        self.assertEqual(self.evaluator.evaluate.call_args.args[3], [])
        self.assertEqual(self.service.sessions[first['session_id']]['score'], 0)
        self.service.end(first['session_id'])
        with self.assertRaises(KeyError):
            self.service.next(first['session_id'], first['question']['id'])


if __name__ == '__main__':
    unittest.main()
