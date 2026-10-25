import argparse
import base64
import json
from pathlib import Path
import sys
import time

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quiz_cache import QuestionCache
from quiz_curriculum import SUBJECTS
from quiz_preparation import cache_namespace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', default='http://127.0.0.1:8000')
    parser.add_argument('--grade', type=int, choices=range(1, 7), default=2)
    parser.add_argument('--subject', choices=SUBJECTS, default='mixto')
    parser.add_argument('--output', required=True)
    parser.add_argument('--answer-mode', choices=['text', 'letters'], default='text')
    args = parser.parse_args()
    root = args.server.rstrip('/')
    records = []
    report = {'grade': args.grade, 'subject': args.subject, 'records': records, 'first_try_correct': 0, 'clarifications': 0, 'cache_namespace': cache_namespace(), 'answer_mode': args.answer_mode}

    def save():
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    def call(route, payload):
        started = time.monotonic()
        response = requests.post(root + '/quiz/' + route, json=payload, timeout=30)
        elapsed = round((time.monotonic() - started) * 1000)
        response.raise_for_status()
        data = response.json()
        if response.status_code != 200:
            raise RuntimeError(f'{route}: {response.status_code} {data}')
        if route != 'end':
            choices = data['question']['options']
            if len(choices) != 4 or len({choice['text'].casefold() for choice in choices}) != 4:
                raise RuntimeError('La pregunta no tiene cuatro opciones distintas.')
            if route in {'start', 'next'} and not all(f'{choice["label"]}:' in data['response'] for choice in choices):
                raise RuntimeError('La narración no incluye las cuatro opciones.')
            audio = base64.b64decode(data.get('audio', '').partition(',')[2])
            if not audio.startswith(b'RIFF') or audio[8:12] != b'WAVE':
                raise RuntimeError('No se recibió audio WAV.')
            record = {'route': route, 'elapsed_ms': elapsed, 'audio_bytes': len(audio),
                      'phase': data['phase'], 'question': data['question']['prompt'], 'source': data['question'].get('source'), 'options': choices,
                      'feedback': data.get('feedback'), 'evaluation': data.get('evaluation'), 'score': data['score']}
            records.append(record)
            print(json.dumps({key: record[key] for key in ('route', 'elapsed_ms', 'phase', 'score')}, ensure_ascii=False), flush=True)
            save()
        return data

    status = requests.get(root + '/quiz/prepare', params={'grade': args.grade, 'subject': args.subject}, timeout=5).json()
    if status['state'] != 'ready':
        raise RuntimeError('Ejecuta prepare_quiz.py primero.')
    cache = QuestionCache(cache_namespace())
    questions = [question for subject in SUBJECTS if subject != 'mixto' for question in cache.questions(args.grade, subject)]
    references = {question['prompt']: question for question in questions}
    game = call('start', {'grade': args.grade, 'subject': args.subject})
    sid = game['session_id']
    try:
        qid = game['question']['id']
        repeated = call('answer', {'session_id': sid, 'question_id': qid, 'answer': '¿Puedes repetir? No escuché.'})
        if repeated['audio'] != game['audio']:
            raise RuntimeError('Repetir debe reutilizar el audio preparado.')
        if repeated['phase'] != 'question' or repeated['score'] != 0:
            raise RuntimeError('Repetir no debe consumir la pregunta.')
        for index in range(5):
            qid = game['question']['id']
            reference = references[game['question']['prompt']]['answer']
            if args.answer_mode == 'letters':
                label = next(choice['label'] for choice in game['question']['options'] if choice['text'] == reference)
                answer = f'Yo creo que la opción {label}.'
            else:
                answer = f'Pues yo creo que es {reference}, eso es lo que pienso.'
            response = call('answer', {'session_id': sid, 'question_id': qid, 'answer': answer})
            records[-1]['spoken_answer'] = answer
            report['first_try_correct'] += int(response['feedback']['kind'] == 'correct')
            if response['phase'] == 'question':
                report['clarifications'] += 1
                followup = references[game['question']['prompt']]['support']
                response = call('answer', {'session_id': sid, 'question_id': qid, 'answer': followup})
                records[-1]['spoken_answer'] = followup
            if response['phase'] == 'question':
                response = call('answer', {'session_id': sid, 'question_id': qid, 'answer': 'No sé la respuesta.'})
            if response['phase'] == 'question':
                raise RuntimeError('No fue posible continuar después de la aclaración.')
            if index < 4:
                game = call('next', {'session_id': sid, 'question_id': qid})
        report['completed'] = response['phase'] == 'finished'
        report['score'] = response['score']
        save()
        return int(not report['completed'])
    finally:
        call('end', {'session_id': sid})


if __name__ == '__main__':
    raise SystemExit(main())
