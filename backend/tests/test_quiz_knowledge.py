import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from langchain_core.documents import Document

from quiz_curriculum import SUBJECTS
from quiz_knowledge import DATA_PATH, EducationKnowledge, Lesson


class KnowledgeTests(unittest.TestCase):
    def test_local_sources_cover_all_subjects_and_grades(self):
        lessons = [Lesson.model_validate(row) for row in json.loads(DATA_PATH.read_text(encoding='utf-8'))]
        self.assertEqual(len({lesson.id for lesson in lessons}), len(lessons))
        for grade in range(1, 7):
            for subject in set(SUBJECTS) - {'mixto'}:
                self.assertTrue(any(row.subject == subject and row.min_grade <= grade <= row.max_grade for row in lessons))

    def test_index_is_updated_only_when_material_changes_and_retrieval_filters_grade(self):
        lesson = json.loads(DATA_PATH.read_text(encoding='utf-8'))[0]
        store = Mock()
        store.get.return_value = {'ids': [], 'metadatas': []}
        doc = Document(page_content=lesson['text'], metadata=lesson)
        store.similarity_search.return_value = [doc]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'lessons.json'
            path.write_text(json.dumps([lesson]))
            knowledge = EducationKnowledge(path, store_factory=lambda: store)
            self.assertEqual(knowledge.retrieve(1, lesson['subject']), [doc])
            knowledge.retrieve(2, lesson['subject'])
            store.add_documents.assert_called_once()
            filters = store.similarity_search.call_args.kwargs['filter']['$and']
            self.assertIn({'min_grade': {'$lte': 2}}, filters)
            self.assertIn({'max_grade': {'$gte': 2}}, filters)
            metadata = store.add_documents.call_args.args[0][0].metadata
            store.get.return_value = {'ids': [lesson['id']], 'metadatas': [metadata]}
            store.add_documents.reset_mock()
            EducationKnowledge(path, store_factory=lambda: store).retrieve(1, lesson['subject'])
            store.add_documents.assert_not_called()

    def test_missing_material_does_not_fall_back_to_another_subject(self):
        store = Mock()
        store.get.return_value = {'ids': [], 'metadatas': []}
        store.similarity_search.return_value = []
        knowledge = EducationKnowledge(store_factory=lambda: store)
        with self.assertRaises(ValueError):
            knowledge.retrieve(2, 'espanol')


if __name__ == '__main__':
    unittest.main()
