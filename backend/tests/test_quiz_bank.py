import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from quiz_bank import FILLERS, AudioCache, BankQuestionProvider, load_bank, to_question
from quiz_curriculum import SUBJECTS
from quiz_engine import QuizService
from quiz_narration import feedback_texts, question_narration


class BankTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.audio = AudioCache(Path(self.temp.name) / 'audio.sqlite3')
        self.provider = BankQuestionProvider(audio=self.audio, synthesize=lambda text: f'wav:{text}')

    def tearDown(self):
        self.temp.cleanup()

    def test_bank_is_valid_and_every_grade_and_subject_can_play_a_round(self):
        rows = load_bank()
        self.assertGreaterEqual(len(rows), 90)
        for row in rows:
            self.assertIn(row.answer, to_question(row)['options'])
        for grade in range(1, 7):
            for subject in SUBJECTS:
                with self.subTest(grade=grade, subject=subject):
                    self.assertEqual(self.provider.status(grade, subject)['state'], 'ready')
                    questions = self.provider.generate_round(grade, subject)
                    self.assertEqual(len({q['bank_id'] for q in questions}), 5)
                    self.assertTrue(all(q['grades'][0] <= grade <= q['grades'][1] for q in questions))

    def test_mixed_round_has_one_question_per_subject(self):
        questions = self.provider.generate_round(3, 'mixto', random.Random(1))
        self.assertEqual({q['subject'] for q in questions}, {name for key, name in SUBJECTS.items() if key != 'mixto'})

    def test_option_order_is_stable_so_its_voice_can_be_prepared_once(self):
        row = load_bank()[0]
        self.assertEqual(to_question(row)['options'], to_question(row)['options'])
        self.assertEqual(len({tuple(to_question(r)['options']).index(r.answer) for r in load_bank()}), 4)

    def test_rounds_rotate_through_the_bank_before_repeating(self):
        pool = self.provider._pool(1, 'biologia')
        seen = []
        for _ in range(len(pool) // 5):
            seen += [q['bank_id'] for q in self.provider.generate_round(1, 'biologia')]
        self.assertEqual(len(seen), len(set(seen)))
        restarted = BankQuestionProvider(audio=AudioCache(self.audio.path), synthesize=None)
        self.assertEqual(restarted.audio.usage()[seen[0]][0], 1)

    def test_warm_audio_synthesizes_missing_voices_once(self):
        calls = Mock(side_effect=lambda text: 'wav')
        provider = BankQuestionProvider(bank=load_bank()[:2], audio=self.audio, synthesize=calls)
        provider._warm()
        first = calls.call_count
        self.assertEqual(first, 2 + len(FILLERS))
        provider._warm()
        self.assertEqual(calls.call_count, first)
        self.assertEqual(self.audio.get(question_narration(provider.questions[0])), 'wav')

    def test_round_reuses_prepared_question_voice_and_speaks_the_model_reply_live(self):
        BankQuestionProvider(bank=load_bank(), audio=self.audio, synthesize=lambda text: 'wav-ok')._warm()
        evaluator = Mock()
        service = QuizService(evaluator, BankQuestionProvider(audio=self.audio, synthesize=None))
        game = service.start(2, 'mixto')
        self.assertEqual(game['_prepared_audio'], 'wav-ok')
        current = service.sessions[game['session_id']]['questions'][0]
        evaluator.evaluate.return_value = {'status': 'correct', 'feedback': '¡Eso, muy bien pensado!'}
        response = service.answer(game['session_id'], game['question']['id'], 'mi respuesta')
        self.assertIsNone(response['_prepared_audio'])
        self.assertEqual(response['response'], '¡Eso, muy bien pensado!')
        self.assertEqual(response['score'], 1)

    def test_fillers_are_served_once_their_voice_is_ready(self):
        self.assertEqual(self.provider.fillers(), [])
        self.audio.put(FILLERS[0], 'wav-filler')
        self.assertEqual(self.provider.fillers(), [{'text': FILLERS[0], 'audio': 'wav-filler'}])


class ChildAnswerFixtureTests(unittest.TestCase):
    def test_live_interpretation_cases_refer_to_real_bank_questions(self):
        ids = {row.id for row in load_bank()}
        for name in ('respuestas_ninos.json', 'respuestas_ninos_validacion.json'):
            cases = json.loads((Path(__file__).parent / 'fixtures' / name).read_text(encoding='utf-8'))
            self.assertTrue(cases)
            for case in cases:
                self.assertIn(case['bank_id'], ids)
                self.assertIn(case['esperado'], {'correct', 'incorrect', 'unclear', 'not_correct'})


if __name__ == '__main__':
    unittest.main()
