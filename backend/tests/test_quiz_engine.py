import unittest

from quiz_engine import QuizService, SUBJECTS, pick_answer


class QuizTests(unittest.TestCase):
    def setUp(self):
        self.service = QuizService()

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
                        result = self.service.answer(game['session_id'], qid, expected)
                        self.assertEqual(result['score'], index + 1)
                        self.assertEqual(result['answered'], index + 1)
                        if index < 4:
                            game = self.service.next(game['session_id'], qid)
                    self.assertEqual(result['phase'], 'finished')
                    self.assertEqual(result['score'], 5)
                    self.assertEqual(len(ids), 5)

    def test_wrong_answer_gives_explanation_without_a_point(self):
        game = self.service.start(2, 'biologia')
        question = self.service.sessions[game['session_id']]['questions'][0]
        wrong = next(option for option in question['options'] if option != question['answer'])
        result = self.service.answer(game['session_id'], question['id'], wrong)
        self.assertFalse(result['feedback']['correct'])
        self.assertEqual(result['score'], 0)
        self.assertIn(question['answer'], result['feedback']['text'])
        self.assertIn(question['explanation'], result['feedback']['text'])

    def test_retries_do_not_count_or_skip_twice(self):
        game = self.service.start(3, 'matematicas')
        question = self.service.sessions[game['session_id']]['questions'][0]
        result = self.service.answer(game['session_id'], question['id'], question['answer'])
        self.assertEqual(self.service.answer(game['session_id'], question['id'], question['answer']), result)
        next_question = self.service.next(game['session_id'], question['id'])
        self.assertEqual(self.service.next(game['session_id'], question['id']), next_question)
        self.assertEqual(next_question['answered'], 1)

    def test_invalid_input_and_premature_next_preserve_question(self):
        game = self.service.start(4, 'geografia')
        qid = game['question']['id']
        with self.assertRaises(ValueError):
            self.service.answer(game['session_id'], qid, 'una respuesta que no es una opción')
        with self.assertRaises(ValueError):
            self.service.next(game['session_id'], qid)
        self.assertFalse(self.service.sessions[game['session_id']]['answers'])

    def test_spoken_numbers_accents_and_explicit_letters(self):
        question = {'options': ['2', '6', '8', '4']}
        self.assertEqual(pick_answer('seis', question), '6')
        self.assertEqual(pick_answer('opción B', question), '6')
        self.assertEqual(pick_answer('son seis', question), '6')
        self.assertIsNone(pick_answer('No sé', question))
        letters = {'options': ['B', 'A', 'D', 'F']}
        self.assertEqual(pick_answer('A', letters), 'A')
        self.assertEqual(pick_answer('opción A', letters), 'B')
        organs = {'options': ['Los pulmones', 'Los huesos', 'Los dientes', 'Los ojos']}
        self.assertEqual(pick_answer('son los pulmones', organs), 'Los pulmones')
        self.assertEqual(pick_answer('ce', {'options': ['C', 'M', 'P', 'S']}), 'C')
        self.assertEqual(pick_answer('un perro', {'options': ['El perro', 'La mariposa', 'La gallina', 'La rana']}), 'El perro')

    def test_participants_are_separate_and_can_end(self):
        first = self.service.start(1, 'matematicas')
        second = self.service.start(6, 'espanol')
        question = self.service.sessions[first['session_id']]['questions'][0]
        self.service.answer(first['session_id'], question['id'], question['answer'])
        self.assertEqual(self.service.sessions[second['session_id']]['score'], 0)
        self.assertFalse(self.service.sessions[second['session_id']]['answers'])
        self.service.end(first['session_id'])
        with self.assertRaises(KeyError):
            self.service.next(first['session_id'], question['id'])


if __name__ == '__main__':
    unittest.main()
