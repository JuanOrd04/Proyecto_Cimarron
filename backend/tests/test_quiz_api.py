import unittest
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import quiz_api


class QuizApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(quiz_api.router)
        self.client = TestClient(app)
        self.service = patch('quiz_api.quiz_service', new=Mock()).start()
        self.speak = patch('quiz_api.speak', return_value='feedback-wav').start()
        self.addCleanup(patch.stopall)
        self.addCleanup(self.client.close)

    def test_preparation_poll_only_reads_status_and_validates_grade(self):
        self.service.generator.status.return_value = {'state': 'ready', 'ready': 5, 'required': 5}
        response = self.client.get('/quiz/prepare?grade=2&subject=mixto')
        self.assertEqual(response.status_code, 200)
        self.service.generator.status.assert_called_once_with(2, 'mixto')
        self.service.prepare.assert_not_called()
        self.speak.assert_not_called()
        self.assertEqual(self.client.get('/quiz/prepare?grade=9&subject=mixto').status_code, 422)

    def test_fillers_endpoint_returns_only_prepared_fillers(self):
        self.service.generator.fillers.return_value = [{'text': '¡A ver!', 'audio': 'wav'}]
        response = self.client.get('/quiz/fillers')
        self.assertEqual(response.json(), {'fillers': [{'text': '¡A ver!', 'audio': 'wav'}]})
        self.speak.assert_not_called()

    def test_question_audio_is_reused_and_internal_audio_field_is_removed(self):
        self.service.next.return_value = {'response': 'Mi pregunta', '_prepared_audio': 'prepared-wav'}
        response = self.client.post('/quiz/next', json={'session_id': 'session', 'question_id': 'question'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'response': 'Mi pregunta', 'audio': 'prepared-wav'})
        self.speak.assert_not_called()

    def test_feedback_still_uses_live_voice(self):
        self.service.answer.return_value = {'response': 'Mi explicación', '_prepared_audio': None}
        response = self.client.post('/quiz/answer', json={'session_id': 'session', 'question_id': 'question', 'answer': 'Creo que... '})
        self.assertEqual(response.status_code, 200)
        self.speak.assert_called_once_with('Mi explicación')
        self.assertEqual(response.json()['audio'], 'feedback-wav')


if __name__ == '__main__':
    unittest.main()
