import json
import unittest
from unittest.mock import Mock

from ollama_client import QUIZ_MODEL_NAME, OllamaError, quiz_client
from quiz_dialogue import CLARIFICATION, choice_schema, reveals_answer
from quiz_llm import OllamaQuizEvaluator, QuizModelUnavailable
from quiz_narration import feedback_texts, hint_text, question_narration

REPLY_START = 'Eres el Cimarrón, la mascota'


class ChoiceDialogueTests(unittest.TestCase):
    def setUp(self):
        self.llm = Mock(model_name='qwen2.5:7b')
        self.evaluator = OllamaQuizEvaluator(self.llm)
        self.question = {'prompt': '¿Qué necesita una planta para crecer?', 'answer': 'Agua',
                         'options': ['Un perro', 'Agua', 'Una piedra', 'Un juguete'], 'answer_kind': 'fact',
                         'explanation': 'Las plantas toman agua por sus raíces.',
                         'support': 'Las plantas necesitan agua, luz, aire y minerales.',
                         'hint': 'Piensa en lo que le das a una maceta con una regadera.'}

    def replies(self, *rows, reply='¡Eso es, el agüita!'):
        queue = [json.dumps(row, ensure_ascii=False) for row in rows]

        def generate(prompt, **kwargs):
            if prompt.startswith(REPLY_START):
                if isinstance(reply, Exception):
                    raise reply
                return json.dumps({'feedback': reply}, ensure_ascii=False)
            return queue.pop(0)
        self.llm.generate.side_effect = generate

    def judged_calls(self):
        return [call for call in self.llm.generate.call_args_list if not call.args[0].startswith(REPLY_START)]

    def reply_prompt(self):
        return next(call.args[0] for call in self.llm.generate.call_args_list if call.args[0].startswith(REPLY_START))

    def test_meaning_of_spoken_answer_is_mapped_to_an_option_with_one_request(self):
        self.replies({'lo_que_dijo': 'agüita', 'eleccion': 'B) Agua'})
        result = self.evaluator.evaluate(self.question, 'creo que es agüita', 2)
        self.assertEqual(result['status'], 'correct')
        self.assertEqual(result['interpreted_answer'], 'Agua')
        self.assertEqual(result['feedback'], '¡Eso es, el agüita!')
        self.assertEqual(len(self.judged_calls()), 1)
        prompt = self.judged_calls()[0].args[0]
        self.assertIn('creo que es agüita', prompt)
        self.assertNotIn(self.question['prompt'], prompt)
        self.assertNotIn('respuesta_esperada', prompt)
        self.assertNotIn(self.question['support'], prompt)
        self.assertLessEqual(self.judged_calls()[0].kwargs['timeout'], 15)

    def test_graded_reply_is_written_by_the_model_knowing_the_answer_and_the_round(self):
        self.replies({'lo_que_dijo': 'un perrito', 'eleccion': 'A) Un perro'}, reply='Casi, era el agua.')
        context = {'numero_de_pregunta': 2, 'total': 5, 'aciertos_hasta_ahora': 1, 'resultados_anteriores': []}
        result = self.evaluator.evaluate(self.question, 'un perrito', 2, (), context)
        self.assertEqual(result['status'], 'incorrect')
        self.assertEqual(result['feedback'], 'Casi, era el agua.')
        self.assertFalse(result['closing_included'])
        prompt = self.reply_prompt()
        self.assertIn('"respuesta_correcta": "Agua"', prompt)
        self.assertIn(self.question['explanation'], prompt)
        self.assertIn('"aciertos_hasta_ahora": 1', prompt)

    def test_last_question_reply_closes_the_round_with_the_total(self):
        self.replies({'lo_que_dijo': 'agua', 'eleccion': 'B) Agua'}, reply='¡Acertaste 4 de 5!')
        context = {'numero_de_pregunta': 5, 'total': 5, 'aciertos_hasta_ahora': 3, 'resultados_anteriores': []}
        result = self.evaluator.evaluate(self.question, 'agua', 2, (), context)
        self.assertTrue(result['closing_included'])
        self.assertIn('"aciertos_totales": 4', self.reply_prompt())

    def test_failed_reply_falls_back_to_a_fixed_clarification(self):
        self.replies({'lo_que_dijo': 'eh', 'eleccion': 'RUIDO_O_INDECISION'}, reply=OllamaError('lento'))
        result = self.evaluator.evaluate(self.question, 'eh', 2)
        self.assertEqual(result['status'], 'unclear')
        self.assertEqual(result['feedback'], CLARIFICATION)

    def test_child_question_is_answered_from_the_teacher_guide_without_the_answer(self):
        self.replies({'lo_que_dijo': '¿me das una pista?', 'eleccion': 'PREGUNTA_DEL_NINO'},
                     reply='Piensa en tu regadera, ¿qué le echas a la maceta?')
        result = self.evaluator.evaluate(self.question, '¿me das una pista?', 2)
        self.assertEqual(result['status'], 'unclear')
        self.assertEqual(result['feedback'], 'Piensa en tu regadera, ¿qué le echas a la maceta?')
        self.assertIn(self.question['hint'], self.reply_prompt())
        self.assertNotIn('respuesta_correcta', self.reply_prompt())

    def test_reply_that_reveals_the_answer_is_rewritten_then_replaced_by_the_guide(self):
        self.replies({'lo_que_dijo': '¿me das una pista?', 'eleccion': 'PREGUNTA_DEL_NINO'}, reply='Necesita agua.')
        result = self.evaluator.evaluate(self.question, '¿me das una pista?', 2)
        reply_calls = [c for c in self.llm.generate.call_args_list if c.args[0].startswith(REPLY_START)]
        self.assertEqual(len(reply_calls), 2)
        self.assertIn('revelaba la respuesta', reply_calls[1].args[0])
        self.assertEqual(result['feedback'], hint_text(self.question))

    def test_unclear_reply_never_sees_the_answer_and_cannot_reveal_it(self):
        self.replies({'lo_que_dijo': 'la... la...', 'eleccion': 'RUIDO_O_INDECISION'}, reply='¿Dijiste agua?')
        result = self.evaluator.evaluate(self.question, 'la... la...', 2)
        self.assertEqual(result['status'], 'unclear')
        self.assertEqual(result['feedback'], CLARIFICATION)
        self.assertNotIn('respuesta_correcta', self.reply_prompt())
        self.assertNotIn(self.question['explanation'], self.reply_prompt())

    def test_number_answer_is_detected_as_digits_or_words(self):
        q = {**self.question, 'answer': '42', 'answer_kind': 'number'}
        self.assertTrue(reveals_answer(q, 'Son 42 en total.'))
        self.assertTrue(reveals_answer(q, 'Te quedan cuarenta y dos.'))
        self.assertFalse(reveals_answer(q, 'Junta las dos cantidades.'))

    def test_plural_of_the_answer_also_counts_as_revealing_it(self):
        q = {**self.question, 'answer': 'El oído'}
        self.assertTrue(reveals_answer(q, 'Usa tus oídos para escuchar.'))
        self.assertFalse(reveals_answer(q, 'Piensa en lo que usas cuando alguien te habla bajito.'))

    def test_schema_only_allows_the_question_options_or_special_intents(self):
        schema = choice_schema(self.question['options']).model_json_schema()
        allowed = schema['properties']['eleccion']['enum']
        self.assertEqual(allowed[:4], ['A) Un perro', 'B) Agua', 'C) Una piedra', 'D) Un juguete'])
        self.assertEqual(set(allowed[4:]), {'PEDIR_REPETIR', 'NO_SABE', 'RUIDO_O_INDECISION',
                                            'RESPUESTA_FUERA_DE_OPCIONES', 'PREGUNTA_DEL_NINO'})

    def test_answer_outside_the_options_is_judged_by_the_model(self):
        for verdict, status in [(True, 'correct'), (False, 'incorrect')]:
            with self.subTest(verdict=verdict):
                self.llm.reset_mock()
                self.replies({'lo_que_dijo': 'que le dé el sol', 'eleccion': 'RESPUESTA_FUERA_DE_OPCIONES'},
                             {'razonamiento': 'La luz también es necesaria.', 'correcta': verdict})
                result = self.evaluator.evaluate(self.question, 'que le dé el sol', 2)
                self.assertEqual(result['status'], status)
                self.assertEqual(len(self.judged_calls()), 2)
                self.assertIn('que le dé el sol', self.judged_calls()[1].args[0])

    def test_repeat_reuses_question_narration_and_never_scores(self):
        self.replies({'lo_que_dijo': '', 'eleccion': 'PEDIR_REPETIR'})
        result = self.evaluator.evaluate(self.question, 'No escuché, ¿otra vez?', 1)
        self.assertEqual(result['status'], 'unclear')
        self.assertEqual(result['feedback'], question_narration(self.question))

    def test_noise_asks_again_without_scoring(self):
        self.replies({'lo_que_dijo': '', 'eleccion': 'RUIDO_O_INDECISION'})
        result = self.evaluator.evaluate(self.question, 'eh', 1)
        self.assertEqual(result['status'], 'unclear')
        self.assertNotIn('respuesta_correcta', self.reply_prompt())

    def test_unknown_is_checked_by_the_judge_before_explaining_the_answer(self):
        self.replies({'lo_que_dijo': 'no sabe', 'eleccion': 'NO_SABE'},
                     {'razonamiento': 'No propuso una respuesta.', 'correcta': False})
        result = self.evaluator.evaluate(self.question, 'No sé', 1)
        self.assertEqual(result['status'], 'incorrect')
        self.assertIn('"respuesta_correcta": "Agua"', self.reply_prompt())
        self.assertEqual(len(self.judged_calls()), 2)

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
                self.assertEqual(len(self.judged_calls()), 1)
                prompt = self.judged_calls()[0].args[0]
                self.assertNotIn('15', prompt)
                self.assertNotIn('22', prompt)
                self.assertIn('Creo que siete.', prompt)

    def test_default_evaluator_uses_the_quiz_model_client(self):
        self.assertIs(OllamaQuizEvaluator().llm, quiz_client)
        self.assertEqual(OllamaQuizEvaluator().model, QUIZ_MODEL_NAME)

    def test_unavailable_model_never_uses_matching_to_award_a_point(self):
        self.llm.generate.side_effect = OllamaError('Modelo apagado')
        with self.assertRaises(QuizModelUnavailable):
            self.evaluator.evaluate(self.question, 'Agua', 2)


if __name__ == '__main__':
    unittest.main()
