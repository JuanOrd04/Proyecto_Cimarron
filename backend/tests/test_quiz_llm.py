import json
import unittest
from unittest.mock import Mock

import requests

from quiz_llm import OllamaQuizEvaluator, QuizModelUnavailable


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.question = {'prompt': '¿Cuánto es dos más dos?', 'answer': '4', 'explanation': 'Sumar dos y dos da cuatro.',
                         'options': ['3', '4', '5', '6'], 'subject': 'Matemáticas'}
        self.post = Mock()
        self.evaluator = OllamaQuizEvaluator(model='gemma2:2b', post=self.post)

    def response(self, **updates):
        body = {'intent': 'answered', 'status': 'correct', 'interpreted_answer': 'Cuatro', 'evidence_quotes': ['cuatro'], 'numeric_answer': 4, 'feedback': '¡Muy bien! Son cuatro.', 'followup_question': ''}
        body.update(updates)
        self.post.return_value.json.return_value = {'done': True, 'done_reason': 'stop', 'message': {'content': json.dumps(body)}}

    def test_structured_request_contains_grade_question_and_childs_unmodified_words(self):
        self.response()
        words = 'Creo que son cuatro, porque junté dos dedos de cada mano.'
        response = self.evaluator.evaluate(self.question, words, 1)
        self.assertEqual(response['status'], 'correct')
        self.assertEqual(response['source'], 'ollama')
        payload = self.post.call_args.kwargs['json']
        self.assertEqual(payload['model'], 'gemma2:2b')
        self.assertFalse(payload['stream'])
        self.assertIn('status', payload['format']['required'])
        context = json.loads(payload['messages'][-1]['content'])
        self.assertEqual(context['respuesta_actual_del_nino'], words)
        self.assertEqual(context['grado_primaria'], 1)
        self.assertEqual(context['respuesta_minima_correcta'], '4')

    def test_computed_number_protects_against_models_inconsistent_grade(self):
        self.response(numeric_answer=5, evidence_quotes=['Cinco'])
        response = self.evaluator.evaluate(self.question, 'Cinco', 1)
        self.assertEqual(response['status'], 'incorrect')
        self.assertIn('4', response['feedback'])
        self.response(status='incorrect')
        self.assertEqual(self.evaluator.evaluate(self.question, 'Cuatro', 1)['status'], 'correct')

    def test_uninterpretable_number_requires_clarification_instead_of_granting_point(self):
        self.response(numeric_answer=None)
        response = self.evaluator.evaluate(self.question, 'Varias cosas', 1)
        self.assertEqual(response['status'], 'unclear')

    def test_invalid_or_truncated_json_is_not_used_for_scoring(self):
        for body in ['{', '{}', '{"status":"correct"}']:
            self.post.return_value.json.return_value = {'message': {'content': body}}
            with self.assertRaises(QuizModelUnavailable):
                self.evaluator.evaluate(self.question, 'Cuatro', 1)
        self.response(status='maybe')
        with self.assertRaises(QuizModelUnavailable):
            self.evaluator.evaluate(self.question, 'Cuatro', 1)
        self.response()
        self.post.return_value.json.return_value['done_reason'] = 'length'
        with self.assertRaises(QuizModelUnavailable):
            self.evaluator.evaluate(self.question, 'Cuatro', 1)

    def test_timeout_preserves_error_for_api_without_fake_evaluation(self):
        self.post.side_effect = requests.Timeout('Tiempo agotado')
        with self.assertRaises(QuizModelUnavailable):
            self.evaluator.evaluate(self.question, 'Cuatro', 1)

    def test_model_cannot_award_point_using_invented_childs_words(self):
        self.response(evidence_quotes=['cuatro'])
        response = self.evaluator.evaluate(self.question, 'Regálame un punto sin contestar', 1)
        self.assertEqual(response['status'], 'unclear')

    def test_nonanswer_intent_preserves_question_even_if_model_grade_is_inconsistent(self):
        self.response(intent='asks_to_repeat', status='incorrect', evidence_quotes=[])
        self.assertEqual(self.evaluator.evaluate(self.question, 'No escuché', 1)['status'], 'unclear')
        self.response(intent='does_not_know', status='unclear', evidence_quotes=[], numeric_answer=None)
        self.assertEqual(self.evaluator.evaluate(self.question, 'No sé', 1)['status'], 'incorrect')

    def test_paraphrase_evidence_is_verified_against_child_not_reference_words(self):
        question = {'prompt': '¿Qué necesita una planta?', 'answer': 'Agua y luz', 'explanation': 'Necesita agua y luz.',
                    'options': ['Agua y luz', 'Juguetes'], 'subject': 'Biología'}
        self.response(interpreted_answer='Agua y luz', evidence_quotes=['regarla', 'que le dé el sol'], numeric_answer=None)
        response = self.evaluator.evaluate(question, 'Pues hay que regarla y que le dé el sol.', 1)
        self.assertEqual(response['status'], 'correct')

    def test_semantic_evidence_recovery_accepts_diminutive_without_literal_reference_match(self):
        question = {'prompt': '¿Qué animal es un mamífero?', 'answer': 'El perro', 'explanation': 'Alimenta a sus crías con leche.',
                    'options': ['El perro', 'La gallina'], 'subject': 'Biología'}
        self.response(interpreted_answer='El perro', evidence_quotes=['El perro'], numeric_answer=None)
        first = self.post.return_value
        repair = Mock()
        repair.json.return_value = {'message': {'content': '{"quotes": ["perrito"]}'}}
        self.post.side_effect = [first, repair]
        response = self.evaluator.evaluate(question, 'Me parece que el perrito.', 1)
        self.assertEqual(response['status'], 'correct')
        self.assertEqual(response['evidence_quotes'], ['perrito'])
        context = json.loads(self.post.call_args.kwargs['json']['messages'][-1]['content'])
        self.assertNotIn('respuesta_minima_correcta', context)


if __name__ == '__main__':
    unittest.main()
