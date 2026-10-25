import unittest
from unittest.mock import ANY, Mock

import requests

from ollama_client import MODEL_NAME, OLLAMA_URL, OllamaClient, OllamaError


class OllamaClientTests(unittest.TestCase):
    def setUp(self):
        self.post = Mock()
        self.post.return_value.json.return_value = {'response': ' Hola ', 'done': True, 'done_reason': 'stop'}
        self.client = OllamaClient(post=self.post)

    def test_chat_preserves_original_model_options_and_endpoint(self):
        self.assertEqual(self.client.generate('Pregunta'), 'Hola')
        self.post.assert_called_once_with(OLLAMA_URL, json={
            'model': MODEL_NAME, 'prompt': 'Pregunta', 'stream': False,
            'keep_alive': '30m',
            'options': {'temperature': 0.1, 'num_predict': 250, 'num_ctx': 4096},
        }, timeout=ANY)
        self.assertGreater(self.post.call_args.kwargs['timeout'], 0)
        self.assertLessEqual(self.post.call_args.kwargs['timeout'], 120)
        self.assertEqual(MODEL_NAME, 'gemma2:2b')

    def test_structured_task_uses_same_model_with_own_schema(self):
        schema, options = {'type': 'object'}, {'temperature': 0, 'num_predict': 100}
        self.client.generate('Evalúa', schema=schema, options=options)
        payload = self.post.call_args.kwargs['json']
        self.assertEqual(payload['model'], MODEL_NAME)
        self.assertEqual(payload['format'], schema)
        self.assertEqual(payload['options'], options)

    def test_timeout_and_http_error_are_reported(self):
        for error in [requests.Timeout(), requests.HTTPError()]:
            with self.subTest(error=type(error).__name__):
                self.post.side_effect = error
                with self.assertRaises(OllamaError):
                    self.client.generate('Pregunta')

    def test_system_instruction_is_forwarded_separately_from_the_task_and_schema(self):
        system = 'Responde en español y conserva las claves del JSON.'
        schema = {'type': 'object'}
        self.client.generate('Evalúa la respuesta del niño.', schema=schema, system=system)
        payload = self.post.call_args.kwargs['json']
        self.assertEqual(payload['system'], system)
        self.assertEqual(payload['prompt'], 'Evalúa la respuesta del niño.')
        self.assertEqual(payload['format'], schema)

    def test_incomplete_or_invalid_response_is_rejected(self):
        for body in [{'response': 7}, {'response': '{}', 'done': False},
                     {'response': '{}', 'done': True, 'done_reason': 'length'}, []]:
            with self.subTest(body=body):
                self.post.return_value.json.return_value = body
                with self.assertRaises(OllamaError):
                    self.client.generate('Pregunta', schema={'type': 'object'})


if __name__ == '__main__':
    unittest.main()
