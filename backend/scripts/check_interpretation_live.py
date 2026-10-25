"""Mide con Ollama real si el juego interpreta bien respuestas infantiles sobre el banco de preguntas.

Uso, desde backend/: ./venv/bin/python scripts/check_interpretation_live.py [archivo_de_casos.json]
"""

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quiz_bank import load_bank, to_question
from quiz_llm import OllamaQuizEvaluator

CASES = Path(__file__).resolve().parents[1] / 'tests' / 'fixtures' / 'respuestas_ninos.json'


def main():
    questions = {row.id: to_question(row) for row in load_bank()}
    evaluator = OllamaQuizEvaluator()
    cases = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else CASES).read_text(encoding='utf-8'))
    hits, times = 0, []
    for case in cases:
        question = questions[case['bank_id']]
        started = time.monotonic()
        result = evaluator.evaluate(question, case['nino_dijo'], question['grades'][0])
        times.append(time.monotonic() - started)
        expected = case['esperado']
        ok = result['status'] != 'correct' if expected == 'not_correct' else result['status'] == expected
        hits += ok
        if not ok:
            print(f'FALLO  {question["prompt"]} | dijo "{case["nino_dijo"]}" -> {result["status"]} '
                  f'(esperado {expected}; entendió "{result["interpreted_answer"]}")', flush=True)
    times.sort()
    print(f'\n{evaluator.model}: {hits}/{len(cases)} correctas ({hits / len(cases):.0%}); '
          f'mediana {times[len(times) // 2]:.2f} s, máximo {times[-1]:.2f} s')
    return 0 if hits == len(cases) else 1


if __name__ == '__main__':
    raise SystemExit(main())
