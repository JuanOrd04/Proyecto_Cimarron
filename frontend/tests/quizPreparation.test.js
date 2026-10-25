import test from 'node:test';
import assert from 'node:assert/strict';
import { observarPreparacionQuiz } from '../src/quizPreparation.js';

const response = (state, ready) => ({ ok: true, json: async () => ({ state, ready, required: 5 }) });

test('Prepara una vez y consulta hasta tener las cinco preguntas; después deja de consultar', async () => {
  const calls = [];
  const states = [];
  let stop;
  await new Promise((resolve, reject) => {
    stop = observarPreparacionQuiz({
      apiBaseUrl: '/api', grade: 2, subject: 'mixto', debounceMs: 0, pollMs: 0,
      fetchImpl: async (url, options) => {
        calls.push([url, options.method]);
        return calls.length === 1 ? response('preparing', 2) : response('ready', 5);
      },
      onUpdate: (data) => { states.push(data.ready); if (data.state === 'ready') resolve(); }, onError: reject,
    });
  });
  stop();
  assert.deepEqual(states, [2, 5]);
  assert.deepEqual(calls, [['/api/quiz/prepare', 'POST'], ['/api/quiz/prepare?grade=2&subject=mixto', 'GET']]);
});

test('Un error de preparación permite reintentar sin quedar consultando en bucle', async () => {
  let calls = 0;
  let stop;
  const error = await new Promise((resolve) => {
    stop = observarPreparacionQuiz({ apiBaseUrl: '', grade: 1, subject: 'espanol', debounceMs: 0, pollMs: 0,
      fetchImpl: async () => { calls += 1; return response('unavailable', 0); },
      onUpdate: () => {}, onError: resolve });
  });
  stop();
  assert.match(error, /reintentar/);
  assert.equal(calls, 1);
});

test('Cambiar de materia descarta el resultado tardío de la materia anterior', async () => {
  let resolveFetch;
  let started;
  const pending = new Promise((resolve) => { started = resolve; });
  const updates = [];
  const stop = observarPreparacionQuiz({ apiBaseUrl: '', grade: 1, subject: 'espanol', debounceMs: 0,
    fetchImpl: () => { started(); return new Promise((resolve) => { resolveFetch = resolve; }); },
    onUpdate: (data) => updates.push(data), onError: (error) => updates.push(error) });
  await pending;
  stop();
  resolveFetch(response('ready', 5));
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(updates, []);
});

test('Una conexión que no responde tiene un plazo y muestra un error recuperable', async () => {
  let stop;
  const error = await new Promise((resolve) => {
    stop = observarPreparacionQuiz({ apiBaseUrl: '', grade: 1, subject: 'mixto', debounceMs: 0, requestTimeoutMs: 5,
      fetchImpl: (url, { signal }) => new Promise((resolve, reject) => {
        signal.addEventListener('abort', () => reject(new Error('abort')), { once: true });
      }), onUpdate: () => {}, onError: resolve });
  });
  stop();
  assert.match(error, /tardando/);
});
