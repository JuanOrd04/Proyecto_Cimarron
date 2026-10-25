import re
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from quiz_prompts import concepts_prompt, evaluation_prompt, ideas_prompt, relation_prompt


class RequiredConcepts(BaseModel):
    model_config = ConfigDict(extra='forbid')
    concepts: list[str] = Field(min_length=1, max_length=6)


class StatedConcepts(BaseModel):
    model_config = ConfigDict(extra='forbid')
    ideas: list[str] = Field(max_length=8)


class ConceptRelation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reason: str = Field(min_length=1, max_length=300)
    relation: Literal['equivalent', 'instance', 'part', 'related', 'unrelated']


class Assessment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['correct', 'partial', 'incorrect', 'unclear']
    feedback: str = Field(min_length=1, max_length=500)


class ConceptEvaluator:
    def __init__(self, request):
        self.request = request

    @lru_cache(maxsize=128)
    def required(self, reference):
        response = self.request(concepts_prompt(reference), RequiredConcepts)
        concepts = tuple(dict.fromkeys(concept.strip() for concept in response.concepts))
        if not concepts or not all(concepts):
            raise ValueError('La rúbrica contiene conceptos vacíos.')
        return concepts

    def check(self, concept, ideas):
        checks = []
        for idea in ideas:
            relation = self.request(relation_prompt(concept, idea), ConceptRelation)
            recognized = relation.relation in {'equivalent', 'instance'}
            checks.append({
                'idea': idea, 'relation': relation.relation,
                'recognized': recognized, 'reason': relation.reason,
            })
            if recognized:
                return {'name': concept, 'state': 'recognized', 'checks': checks}
        return {'name': concept, 'state': 'missing', 'checks': checks}

    def evaluate(self, question, text, grade, previous_turns):
        required = tuple(question.get('required_concepts') or self.required(question['answer']))
        assessment = self.request(evaluation_prompt(question, text, grade, previous_turns), Assessment)
        status, feedback = assessment.status, assessment.feedback.strip()
        if not feedback:
            raise ValueError('Retroalimentación vacía.')
        stated = []
        explicit_option = re.search(r'\bopci[oó]n\s+[a-d]\b', text, re.IGNORECASE) is not None
        check_parts = len(required) > 1 and status in {'correct', 'partial'} and not explicit_option
        if check_parts:
            response = self.request(ideas_prompt(text, previous_turns), StatedConcepts)
            stated = list(dict.fromkeys(idea.strip() for idea in response.ideas if idea.strip()))
            concepts = [self.check(concept, stated) for concept in required]
            count = sum(item['state'] == 'recognized' for item in concepts)
            if not stated or not count:
                status = 'unclear'
            elif count < len(required) or status == 'partial':
                status = 'partial'
            else:
                status = 'correct'
            feedback = ''
        else:
            state = {'correct': 'recognized', 'incorrect': 'missing', 'partial': 'partial', 'unclear': 'unclear'}[status]
            if len(required) > 1 and status != 'correct':
                state = 'not_evaluated'
            concepts = [{'name': concept, 'state': state} for concept in required]
        return {
            'status': status, 'feedback': feedback, 'concepts': concepts, 'student_ideas': stated,
            'matched_concepts': [item['name'] for item in concepts if item['state'] == 'recognized'],
            'missing_concepts': [item['name'] for item in concepts if item['state'] in {'missing', 'partial'}],
            'concepts_evaluated': check_parts or len(required) == 1 or status == 'correct',
            'initial_assessment': assessment.status,
        }
