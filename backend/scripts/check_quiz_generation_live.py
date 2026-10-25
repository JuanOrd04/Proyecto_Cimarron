import argparse
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quiz_curriculum import SUBJECTS
from quiz_generation import OllamaQuestionGenerator
from quiz_llm import OllamaQuizEvaluator


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument('--grade', type=int, choices=range(1, 7), default=2)
    parser.add_argument('--subject', choices=SUBJECTS, default='mixto')
    parser.add_argument('--count', type=int, choices=range(1, 6), default=5)
    parser.add_argument('--evaluate', action='store_true')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    generator = OllamaQuestionGenerator()
    evaluator = OllamaQuizEvaluator()
    previous, records = [], []
    import random
    plan = generator.plan(args.subject, random.Random())
    for subject in plan[:args.count]:
        try:
            question = generator.generate(args.grade, subject, previous)
            record = {'grade': args.grade, 'question': question}
            if args.evaluate:
                record['evaluation'] = evaluator.evaluate(question, f'Creo que es {question["answer"]}.', args.grade)
            previous.append(question)
        except Exception as exc:
            record = {'grade': args.grade, 'subject': subject, 'error': str(exc)}
        records.append(record)
        Path(args.output).write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(record, ensure_ascii=False), flush=True)
    return int(any('error' in record for record in records))


if __name__ == '__main__':
    raise SystemExit(main())
