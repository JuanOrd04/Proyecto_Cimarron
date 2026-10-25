import json
import unittest
from unittest.mock import Mock

from ollama_client import QUIZ_MODEL_NAME, OllamaError, quiz_client
from quiz_llm import OllamaQuizEvaluator, QuizModelUnavailable


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.question = {
            'prompt': '¿Qué necesita una planta para crecer?', 'answer': 'Agua y luz',
            'explanation': 'El agua y la luz ayudan a la planta a crecer.',
            'options': ['Juguetes', 'Agua y luz', 'Una piedra', 'Dulces'],
        }
        self.llm = Mock(model_name='gemma2:2b')
        self.evaluator = OllamaQuizEvaluator(self.llm)

    def responses(self, *bodies):
        bodies = [{**{'reason': 'Interpretación semántica del modelo.'}, **body} if 'relation' in body else body for body in bodies]
        self.llm.generate.side_effect = [json.dumps(body, ensure_ascii=False) for body in bodies]

    def test_default_evaluator_uses_quiz_model_client(self):
        self.assertIs(OllamaQuizEvaluator().llm, quiz_client)
        self.assertEqual(OllamaQuizEvaluator().model, QUIZ_MODEL_NAME)

    def test_generated_question_reuses_its_reviewed_rubric(self):
        question = {**self.question, 'required_concepts': ['Agua', 'Luz']}
        self.responses({'intent': 'answer', 'answer': 'Agua'},
                       {'status': 'partial', 'feedback': '¿Qué más necesita?'}, {'ideas': ['Agua']},
                       {'relation': 'equivalent'}, {'relation': 'unrelated'})
        response = self.evaluator.evaluate(question, 'Creo que agua', 2)
        self.assertEqual(response['status'], 'partial')
        self.assertEqual(response['missing_concepts'], ['Luz'])
        self.assertEqual(self.llm.generate.call_count, 5)

    def test_interpreter_and_child_ideas_do_not_receive_correct_answer(self):
        self.responses({'intent': 'answer', 'answer': 'Creo que agua'}, {'concepts': ['Agua', 'Luz']},
                       {'status': 'correct', 'feedback': 'Respuesta completa.'}, {'ideas': ['Agua']},
                       {'relation': 'equivalent'}, {'relation': 'unrelated'})
        words = 'Creo que hay que darle agua.'
        response = self.evaluator.evaluate(self.question, words, 2)
        interpretation, rubric, assessment, ideas, *_ = self.llm.generate.call_args_list
        self.assertIn(words, interpretation.args[0])
        self.assertNotIn('respuesta_minima', interpretation.args[0])
        self.assertNotIn(self.question['prompt'], interpretation.args[0])
        self.assertNotIn(self.question['answer'], interpretation.args[0])
        self.assertIn(self.question['answer'], rubric.args[0])
        self.assertNotIn(words, rubric.args[0])
        self.assertIn(words, assessment.args[0])
        self.assertIn('"grado_primaria": 2', assessment.args[0])
        self.assertIn(words, ideas.args[0])
        self.assertNotIn(self.question['answer'], ideas.args[0])
        self.assertEqual(response['status'], 'partial')
        self.assertEqual(response['initial_assessment'], 'correct')
        self.assertEqual(response['model'], 'gemma2:2b')

    def test_missing_concept_prevents_point_even_when_general_assessment_says_correct(self):
        self.responses({'intent': 'answer', 'answer': 'Agua'}, {'concepts': ['Agua', 'Luz']},
                       {'status': 'correct', 'feedback': 'Muy bien, agua y luz.'}, {'ideas': ['Agua']},
                       {'relation': 'equivalent'}, {'relation': 'unrelated'})
        response = self.evaluator.evaluate(self.question, 'Creo que agua', 1)
        self.assertEqual(response['status'], 'partial')
        self.assertEqual(response['matched_concepts'], ['Agua'])
        self.assertEqual(response['missing_concepts'], ['Luz'])
        self.assertTrue(response['concepts_evaluated'])
        self.assertIn('Agua', response['feedback'])
        self.assertIn('?', response['feedback'])
        self.assertNotIn('luz', response['feedback'].lower())

    def test_followup_combines_previous_child_words_without_tutor_clarification(self):
        self.responses({'intent': 'answer', 'answer': 'También luz'}, {'concepts': ['Agua', 'Luz']},
                       {'status': 'correct', 'feedback': 'Muy bien.'}, {'ideas': ['Agua', 'Luz']},
                       {'relation': 'equivalent'}, {'relation': 'unrelated'}, {'relation': 'equivalent'})
        previous = [{'respuesta': 'Agua', 'aclaracion': '¿Qué otra cosa falta?'}]
        response = self.evaluator.evaluate(self.question, 'También luz', 2, previous)
        prompt = self.llm.generate.call_args_list[3].args[0]
        self.assertIn('Agua', prompt)
        self.assertIn('También luz', prompt)
        self.assertNotIn(previous[0]['aclaracion'], prompt)
        self.assertEqual(response['status'], 'correct')
        self.assertEqual(response['missing_concepts'], [])

    def test_wrong_answer_is_not_upgraded_by_a_concept_check(self):
        self.responses({'intent': 'answer', 'answer': 'Juguetes'}, {'concepts': ['Agua', 'Luz']},
                       {'status': 'incorrect', 'feedback': 'Las plantas necesitan agua y luz.'})
        response = self.evaluator.evaluate(self.question, 'Juguetes', 1)
        self.assertEqual(response['status'], 'incorrect')
        self.assertFalse(response['concepts_evaluated'])
        self.assertTrue(all(concept['state'] == 'not_evaluated' for concept in response['concepts']))
        self.assertEqual(self.llm.generate.call_count, 3)

    def test_option_syntax_does_not_determine_correctness(self):
        self.responses({'intent': 'answer', 'answer': 'La opción A'}, {'concepts': ['Agua', 'Luz']},
                       {'status': 'incorrect', 'feedback': 'Los juguetes no ayudan a crecer.'})
        response = self.evaluator.evaluate(self.question, 'Creo que la opción A', 1)
        self.assertEqual(response['status'], 'incorrect')
        self.assertEqual(response['matched_concepts'], [])

    def test_repeat_reads_question_and_options_without_consuming_turn(self):
        self.responses({'intent': 'repeat', 'answer': ''})
        response = self.evaluator.evaluate(self.question, 'No escuché', 1)
        self.assertEqual(response['status'], 'unclear')
        self.assertIn(self.question['prompt'], response['feedback'])
        self.assertIn('Opciones:', response['feedback'])
        self.assertEqual(self.llm.generate.call_count, 1)

    def test_nonanswer_does_not_call_assessor_or_award_a_point(self):
        for intent, expected in [('ambiguous', 'unclear'), ('instruction', 'unclear'), ('unknown', 'incorrect')]:
            with self.subTest(intent=intent):
                self.llm.reset_mock()
                self.responses({'intent': intent, 'answer': ''})
                self.assertEqual(self.evaluator.evaluate(self.question, 'No sé', 1)['status'], expected)
                self.assertEqual(self.llm.generate.call_count, 1)

    def test_numeric_interpretation_is_checked_against_computed_result(self):
        question = {**self.question, 'prompt': '¿Cuánto es dos más dos?', 'answer': '4',
                    'options': ['3', '4', '5', '6'], 'explanation': 'Dos y dos son cuatro.'}
        for number, expected in [(4, 'correct'), (5, 'incorrect'), (None, 'unclear')]:
            with self.subTest(number=number):
                self.responses({'intent': 'answer', 'answer': 'Cinco'}, {'number': number})
                response = self.evaluator.evaluate(question, 'Cuatro no, cinco.', 1)
                self.assertEqual(response['status'], expected)
                self.assertEqual(response['numeric_answer'], number)
                self.assertNotIn('respuesta_minima', self.llm.generate.call_args.args[0])

    def test_invalid_output_or_transport_error_does_not_produce_a_grade(self):
        for output in ['{', '{}', '{"intent":"maybe","answer":"agua"}']:
            with self.subTest(output=output):
                self.llm.generate.side_effect = None
                self.llm.generate.return_value = output
                with self.assertRaises(QuizModelUnavailable):
                    self.evaluator.evaluate(self.question, 'agua', 1)
        self.llm.generate.side_effect = OllamaError('No disponible')
        with self.assertRaises(QuizModelUnavailable):
            self.evaluator.evaluate(self.question, 'agua', 1)

    def test_empty_rubric_or_invalid_relation_preserves_error(self):
        self.responses({'intent': 'answer', 'answer': 'Agua'}, {'concepts': [' ']})
        with self.assertRaises(QuizModelUnavailable):
            self.evaluator.evaluate(self.question, 'Agua', 1)
        self.responses({'intent': 'answer', 'answer': 'Agua'}, {'concepts': ['Agua', 'Luz']},
                       {'status': 'correct', 'feedback': 'Bien.'}, {'ideas': ['Agua']}, {'relation': 'unknown'})
        with self.assertRaises(QuizModelUnavailable):
            self.evaluator.evaluate(self.question, 'Agua', 1)

    def test_only_rubric_is_cached_not_participant_answers(self):
        question = {**self.question, 'answer': 'El Sol'}
        self.responses({'intent': 'answer', 'answer': 'La Luna'}, {'concepts': ['Sol']},
                       {'status': 'incorrect', 'feedback': 'Es el Sol.'},
                       {'intent': 'answer', 'answer': 'El Sol'}, {'status': 'correct', 'feedback': 'Muy bien.'})
        self.assertEqual(self.evaluator.evaluate(question, 'La Luna', 1)['status'], 'incorrect')
        self.assertEqual(self.evaluator.evaluate(question, 'El Sol', 1)['status'], 'correct')
        self.assertEqual(self.llm.generate.call_count, 5)


if __name__ == '__main__':
    unittest.main()
