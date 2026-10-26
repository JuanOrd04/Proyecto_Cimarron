import json
import unittest
from unittest.mock import Mock, patch

from langchain_core.documents import Document

with patch('langchain_community.embeddings.OllamaEmbeddings'), patch('langchain_chroma.Chroma'):
    from cimarron_agent import CimarronAgent, cimarron_agent

from ollama_client import ollama_client, quiz_client
from quiz_llm import OllamaQuizEvaluator


class SharedModelTests(unittest.TestCase):
    def test_chat_keeps_its_client_and_quiz_uses_the_quiz_client(self):
        self.assertIs(cimarron_agent.llm, ollama_client)
        self.assertIs(OllamaQuizEvaluator().llm, quiz_client)

    def test_chat_preserves_original_prompt_retrieval_and_history(self):
        llm = Mock(model_name='gemma2:2b', url=ollama_client.url)
        llm.generate.return_value = '¡Hola! Tenemos ingeniería.'
        with patch('cimarron_agent.os.path.exists', return_value=False):
            agent = CimarronAgent(llm=llm)
        agent.vectorstore = Mock()
        agent.vectorstore.similarity_search.return_value = [Document(page_content='Información de la facultad.')]
        agent.history = ['Usuario: Hola', 'Cimarrón: Bienvenido']
        self.assertEqual(agent.generate_response('¿Qué hay?'), '¡Hola! Tenemos ingeniería.')
        agent.vectorstore.similarity_search.assert_called_once_with('Hola ¿Qué hay?', k=4)
        prompt = llm.generate.call_args.args[0]
        self.assertIn('MÁXIMO 2 ORACIONES', prompt)
        self.assertIn('Información de la facultad.', prompt)
        self.assertIn('Usuario: ¿Qué hay?', prompt)
        self.assertEqual(agent.history[-1], 'Cimarrón: ¡Hola! Tenemos ingeniería.')

    def test_shared_client_does_not_mix_chat_history_with_quiz(self):
        llm = Mock(model_name='gemma2:2b', url=ollama_client.url)
        llm.generate.side_effect = [json.dumps({'lo_que_dijo': 'el perrito', 'eleccion': 'A) El perro'}),
                                    json.dumps({'feedback': '¡Eso, el perrito!'})]
        with patch('cimarron_agent.os.path.exists', return_value=False):
            agent = CimarronAgent(llm=llm)
        agent.history = ['Usuario: Cuéntame sobre ingeniería']
        question = {'prompt': '¿Qué animal es un mamífero?', 'answer': 'El perro',
                    'options': ['El perro', 'La gallina'], 'explanation': 'Alimenta a sus crías con leche.',
                    'answer_kind': 'fact', 'hint': 'Piensa en un animal con pelo.'}
        response = OllamaQuizEvaluator(llm).evaluate(question, 'El perrito', 2)
        self.assertEqual(response['status'], 'correct')
        self.assertEqual(agent.history, ['Usuario: Cuéntame sobre ingeniería'])
        for call in llm.generate.call_args_list:
            self.assertNotIn('Cuéntame sobre ingeniería', call.args[0])


if __name__ == '__main__':
    unittest.main()
