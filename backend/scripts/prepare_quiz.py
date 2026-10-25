import argparse
import time

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', default='http://127.0.0.1:8000')
    parser.add_argument('--grade', type=int, choices=range(1, 7), default=1)
    parser.add_argument('--subject', choices=['mixto', 'matematicas', 'ciencias_naturales', 'geografia', 'biologia', 'espanol'], default='mixto')
    parser.add_argument('--timeout', type=float, default=180)
    args = parser.parse_args()
    endpoint = args.server.rstrip('/') + '/quiz/prepare'
    payload = {'grade': args.grade, 'subject': args.subject}
    started = time.monotonic()
    try:
        response = requests.post(endpoint, json=payload, timeout=5)
        previous = None
        while True:
            response.raise_for_status()
            status = response.json()
            progress = (status['state'], status['ready'])
            if progress != previous:
                print(f"{status['ready']}/5 preguntas con audio listas ({time.monotonic() - started:.1f} s).", flush=True)
                previous = progress
            if status['state'] == 'ready':
                print('La ronda está preparada. Abre el Cimarrón para jugar.', flush=True)
                return 0
            if status['state'] == 'unavailable' or time.monotonic() - started >= args.timeout:
                print('La preparación no terminó. Revisa Ollama y reintenta; las preguntas ya listas se conservan.', flush=True)
                return 1
            time.sleep(.5)
            response = requests.get(endpoint, params=payload, timeout=5)
    except (requests.RequestException, ValueError, KeyError) as exc:
        print(f'No se pudo consultar la preparación: {exc}', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
