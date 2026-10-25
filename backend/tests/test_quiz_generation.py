import json
import unittest
from unittest.mock import Mock

from langchain_core.documents import Document

from ollama_client import OllamaError, quiz_client
from quiz_generation import OllamaQuestionGenerator, arithmetic_value, validate_quantities, MAX_ATTEMPTS
from quiz_llm import QuizModelUnavailable


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.llm = Mock(model_name='qwen2.5:7b')
        self.knowledge = Mock()
        self.doc = Document(page_content='El sonido se produce mediante vibraciones de un objeto.', metadata={
            'id': 'test-sound', 'source_title': 'Prueba', 'source_url': 'https://example.org/sound',
        })
        self.knowledge.retrieve.return_value = [self.doc]
        self.generator = OllamaQuestionGenerator(self.llm, self.knowledge)
        self.rng = Mock(shuffle=lambda items: None)
        self.draft = {'pregunta': '¿Qué produce el sonido de un objeto?', 'respuesta_correcta': 'vibraciones',
                      'distractores': ['la luz', 'el color', 'el frío'],
                      'explicacion': 'Los objetos suenan cuando vibran.'}
        self.blind = {'razonamiento': 'El sonido viene de las vibraciones.', 'eleccion': 'A'}

    def replies(self, *values):
        self.llm.generate.side_effect = [json.dumps(value, ensure_ascii=False) for value in values]

    def test_one_request_writes_question_options_and_explanation_and_another_answers_blind(self):
        self.assertIs(OllamaQuestionGenerator().llm, quiz_client)
        self.replies(self.draft, self.blind)
        question = self.generator.generate(3, 'ciencias_naturales', rng=self.rng)
        self.assertEqual(question['answer'], 'vibraciones')
        self.assertEqual(question['options'], ['vibraciones', 'la luz', 'el color', 'el frío'])
        self.assertEqual(question['explanation'], self.draft['explicacion'])
        self.assertEqual(question['support'], self.doc.page_content)
        self.assertEqual(question['generation']['lesson_id'], 'test-sound')
        self.assertEqual(question['generation']['review']['method'], 'blind_answer')
        self.assertEqual(self.llm.generate.call_count, 2)
        self.assertIn(self.doc.page_content, self.llm.generate.call_args_list[0].args[0])
        blind = self.llm.generate.call_args_list[1].args[0]
        self.assertNotIn(self.doc.page_content, blind)
        self.assertNotIn(self.draft['explicacion'], blind)

    def test_ambiguous_question_is_regenerated_with_a_correction(self):
        self.replies(self.draft, {**self.blind, 'eleccion': 'VARIAS'}, self.draft, self.blind)
        question = self.generator.generate(3, 'ciencias_naturales', rng=self.rng)
        self.assertEqual(question['generation']['attempts'], 2)
        self.assertIn('ambigua', self.llm.generate.call_args_list[2].args[0])

    def test_no_question_is_delivered_if_blind_answer_never_matches(self):
        self.replies(*[row for _ in range(MAX_ATTEMPTS) for row in (self.draft, {**self.blind, 'eleccion': 'B'})])
        with self.assertRaises(QuizModelUnavailable):
            self.generator.generate(3, 'ciencias_naturales', rng=self.rng)

    def test_background_generation_has_bounded_requests(self):
        self.replies(self.draft, self.blind)
        self.generator.generate(3, 'ciencias_naturales', rng=self.rng)
        for call in self.llm.generate.call_args_list:
            self.assertGreater(call.kwargs['timeout'], 0)
            self.assertLessEqual(call.kwargs['timeout'], 25)
            self.assertEqual(call.kwargs['priority'], 'background')
            self.assertEqual(call.kwargs['options']['num_ctx'], 4096)

    def test_other_subject_does_not_contaminate_generation_context(self):
        self.replies(self.draft, self.blind)
        self.generator.generate(3, 'ciencias_naturales', [
            {'prompt': 'Tienes 20 euros y gastas 10.', 'subject': 'Matemáticas'},
        ], rng=self.rng)
        for call in self.llm.generate.call_args_list:
            self.assertNotIn('20 euros', call.args[0])

    def test_malformed_drafts_are_rejected_before_reaching_a_child(self):
        bad = [
            {**self.draft, 'pregunta': '¿Qué son las vibraciones de un objeto?'},
            {**self.draft, 'pregunta': '¿Qué produce sonido? a) Agua b) Aire'},
            {**self.draft, 'pregunta': '¿Qué produce sonido? ¿Cómo lo hace?'},
            {**self.draft, 'distractores': ['la luz', 'la luz', 'el frío']},
            {**self.draft, 'distractores': ['vibraciones', 'la luz', 'el frío']},
        ]
        for draft in bad:
            with self.subTest(draft=draft):
                self.llm.reset_mock()
                self.replies(*[draft] * MAX_ATTEMPTS)
                with self.assertRaises(QuizModelUnavailable):
                    self.generator.generate(3, 'ciencias_naturales', rng=self.rng)
                self.assertEqual(self.llm.generate.call_count, MAX_ATTEMPTS)

    def test_empty_or_failed_retrieval_never_returns_a_question(self):
        self.knowledge.retrieve.return_value = []
        with self.assertRaises(QuizModelUnavailable):
            self.generator.generate(2, 'biologia')
        self.llm.generate.assert_not_called()
        self.knowledge.retrieve.side_effect = RuntimeError('Índice no disponible')
        with self.assertRaises(QuizModelUnavailable):
            self.generator.generate(2, 'biologia')

    def test_unavailable_model_never_falls_back_to_a_question_bank(self):
        self.llm.generate.side_effect = OllamaError('Sin modelo')
        with self.assertRaises(QuizModelUnavailable):
            self.generator.generate(2, 'biologia')

    def test_math_answer_is_computed_in_python_without_a_second_request(self):
        draft = {'pregunta': 'Tienes 8 fichas y pierdes 3. ¿Cuántas quedan?', 'operacion': '8-3',
                 'respuesta_correcta': '5', 'distractores': ['4', '6', '11'], 'explicacion': 'Restamos las fichas que perdiste.'}
        self.replies(draft)
        question = self.generator.generate(2, 'matematicas', rng=self.rng)
        self.assertEqual(question['answer'], '5')
        self.assertEqual(question['answer_kind'], 'number')
        self.assertEqual(question['options'], ['5', '4', '6', '11'])
        self.assertEqual(question['generation']['expression'], '8-3')
        self.assertEqual(self.llm.generate.call_count, 1)

    def test_math_with_wrong_result_or_foreign_quantities_is_rejected(self):
        draft = {'pregunta': 'Tienes 8 fichas y pierdes 3. ¿Cuántas quedan?', 'operacion': '8-3',
                 'respuesta_correcta': '6', 'distractores': ['4', '5', '11'], 'explicacion': 'Restamos.'}
        foreign = {**draft, 'operacion': '10-5', 'respuesta_correcta': '5', 'distractores': ['4', '6', '11']}
        for bad in (draft, foreign):
            with self.subTest(bad=bad):
                self.replies(*[bad] * MAX_ATTEMPTS)
                with self.assertRaises(QuizModelUnavailable):
                    self.generator.generate(2, 'matematicas', rng=self.rng)

    def test_math_cannot_solve_using_numbers_from_another_question(self):
        validate_quantities('8-3', 'Tienes 8 fichas y pierdes 3. ¿Cuántas quedan?')
        with self.assertRaises(ValueError):
            validate_quantities('100-25', 'Tienes 50 pesos y gastas 20. ¿Cuántos quedan?')

    def test_arithmetic_allows_only_bounded_arithmetic_without_code_execution(self):
        self.assertEqual(arithmetic_value('(12/3)+2*5'), '14')
        for expression in ['__import__("os")', '2**1000', '1/0', 'True+1', '1/3', '-1', '99999999', '[1][0]']:
            with self.subTest(expression=expression):
                with self.assertRaises((ValueError, ZeroDivisionError)):
                    arithmetic_value(expression)

    def test_previous_questions_are_used_for_retrieval_and_repetition_control(self):
        previous = [{'prompt': self.draft['pregunta'], 'subject': 'Ciencias naturales', 'generation': {'lesson_id': 'test-sound'}}]
        self.replies(*[self.draft] * MAX_ATTEMPTS)
        with self.assertRaises(QuizModelUnavailable):
            self.generator.generate(2, 'ciencias_naturales', previous, rng=self.rng)
        self.knowledge.retrieve.assert_called_with(2, 'ciencias_naturales', previous)
        self.assertIn(self.draft['pregunta'], self.llm.generate.call_args_list[0].args[0])


if __name__ == '__main__':
    unittest.main()
