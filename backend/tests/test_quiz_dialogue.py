import json
import unittest
from unittest.mock import Mock

from ollama_client import OllamaError
from quiz_dialogue import CLARIFICATION, choice_schema
from quiz_llm import OllamaQuizEvaluator, QuizModelUnavailable
from quiz_narration import feedback_texts, question_narration


class ChoiceDialogueTests(unittest.TestCase):
    def setUp(self):
        self.llm = Mock(model_name='qwen2.5:7b')
        self.evaluator = OllamaQuizEvaluator(self.llm)
        self.question = {'prompt': '¿Qué necesita una planta para crecer?', 'answer': 'Agua',
                         'options': ['Un perro', 'Agua', 'Una piedra', 'Un juguete'], 'answer_kind': 'fact',
                         'explanation': 'Las plantas toman agua por sus raíces.',
                         'support': 'Las plantas necesitan agua, luz, aire y minerales.'}

    def replies(self, *rows):
        self.llm.generate.side_effect = [json.dumps(row, ensure_ascii=False) for row in rows]

    def test_meaning_of_spoken_answer_is_mapped_to_an_option_with_one_request(self):
        self.replies({'lo_que_dijo': 'agüita', 'eleccion': 'B) Agua'})
        result = self.evaluator.evaluate(self.question, 'creo que es agüita', 2)
        self.assertEqual(result['status'], 'correct')
        self.assertEqual(result['interpreted_answer'], 'Agua')
        self.assertEqual(result['feedback'], feedback_texts(self.question)['correct'])
        self.assertEqual(self.llm.generate.call_count, 1)
        prompt = self.llm.generate.call_args.args[0]
        self.assertIn('creo que es agüita', prompt)
        self.assertNotIn(self.question['prompt'], prompt)
        self.assertNotIn('respuesta_esperada', prompt)
        self.assertNotIn(self.question['support'], prompt)
        self.assertLessEqual(self.llm.generate.call_args.kwargs['timeout'], 15)

    def test_choosing_another_option_is_incorrect_and_explains_the_answer(self):
        self.replies({'lo_que_dijo': 'un perrito', 'eleccion': 'A) Un perro'})
        result = self.evaluator.evaluate(self.question, 'un perrito', 2)
        self.assertEqual(result['status'], 'incorrect')
        self.assertIn('Agua', result['feedback'])
        self.assertIn(self.question['explanation'], result['feedback'])

    def test_schema_only_allows_the_question_options_or_special_intents(self):
        schema = choice_schema(self.question['options']).model_json_schema()
        allowed = schema['properties']['eleccion']['enum']
        self.assertEqual(allowed[:4], ['A) Un perro', 'B) Agua', 'C) Una piedra', 'D) Un juguete'])
        self.assertEqual(set(allowed[4:]), {'PEDIR_REPETIR', 'NO_SABE', 'RUIDO_O_INDECISION', 'RESPUESTA_FUERA_DE_OPCIONES'})

    def test_answer_outside_the_options_is_judged_by_the_model(self):
        for verdict, status in [(True, 'correct'), (False, 'incorrect')]:
            with self.subTest(verdict=verdict):
                self.llm.reset_mock()
                self.replies({'lo_que_dijo': 'que le dé el sol', 'eleccion': 'RESPUESTA_FUERA_DE_OPCIONES'},
                             {'razonamiento': 'La luz también es necesaria.', 'correcta': verdict})
                result = self.evaluator.evaluate(self.question, 'que le dé el sol', 2)
                self.assertEqual(result['status'], status)
                self.assertEqual(self.llm.generate.call_count, 2)
                self.assertIn('que le dé el sol', self.llm.generate.call_args_list[1].args[0])

    def test_repeat_reuses_question_narration_and_never_scores(self):
        self.replies({'lo_que_dijo': '', 'eleccion': 'PEDIR_REPETIR'})
        result = self.evaluator.evaluate(self.question, 'No escuché, ¿otra vez?', 1)
        self.assertEqual(result['status'], 'unclear')
        self.assertEqual(result['feedback'], question_narration(self.question))

    def test_noise_asks_again_without_scoring(self):
        self.replies({'lo_que_dijo': '', 'eleccion': 'RUIDO_O_INDECISION'})
        result = self.evaluator.evaluate(self.question, 'eh', 1)
        self.assertEqual(result['status'], 'unclear')
        self.assertEqual(result['feedback'], CLARIFICATION)

    def test_unknown_is_checked_by_the_judge_before_explaining_the_answer(self):
        self.replies({'lo_que_dijo': 'no sabe', 'eleccion': 'NO_SABE'},
                     {'razonamiento': 'No propuso una respuesta.', 'correcta': False})
        result = self.evaluator.evaluate(self.question, 'No sé', 1)
        self.assertEqual(result['status'], 'incorrect')
        self.assertEqual(result['feedback'], feedback_texts(self.question)['incorrect'])
        self.assertEqual(self.llm.generate.call_count, 2)

    def test_real_answer_misread_as_unknown_still_earns_the_point(self):
        self.replies({'lo_que_dijo': 'agua y sol', 'eleccion': 'NO_SABE'},
                     {'razonamiento': 'Agua es lo que necesita.', 'correcta': True})
        result = self.evaluator.evaluate(self.question, 'agua y sol', 1)
        self.assertEqual(result['status'], 'correct')

    def test_number_is_extracted_without_seeing_the_problem_and_checked_in_python(self):
        q = {**self.question, 'prompt': 'Tienes 15 y quitas 7. ¿Cuántos quedan?', 'answer': '8',
             'options': ['6', '8', '9', '22'], 'answer_kind': 'number'}
        for reply, status in [({'tipo': 'numero', 'numero': 7, 'letra': None}, 'incorrect'),
                              ({'tipo': 'numero', 'numero': 8, 'letra': None}, 'correct'),
                              ({'tipo': 'letra', 'numero': None, 'letra': 'B'}, 'correct'),
                              ({'tipo': 'repetir', 'numero': None, 'letra': None}, 'unclear'),
                              ({'tipo': 'no_se_entiende', 'numero': None, 'letra': None}, 'unclear')]:
            with self.subTest(reply=reply):
                self.llm.reset_mock()
                self.replies({'lo_que_dijo': 'algo', **reply})
                result = self.evaluator.evaluate(q, 'Creo que siete.', 2)
                self.assertEqual(result['status'], status)
                self.assertEqual(self.llm.generate.call_count, 1)
                prompt = self.llm.generate.call_args.args[0]
                self.assertNotIn('15', prompt)
                self.assertNotIn('22', prompt)
                self.assertIn('Creo que siete.', prompt)

    def test_unavailable_model_never_uses_matching_to_award_a_point(self):
        self.llm.generate.side_effect = OllamaError('Modelo apagado')
        with self.assertRaises(QuizModelUnavailable):
            self.evaluator.evaluate(self.question, 'Agua', 2)


if __name__ == '__main__':
    unittest.main()
