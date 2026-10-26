import test from 'node:test';
import assert from 'node:assert/strict';
import { createSpeechSession } from '../src/utils/speechRecognitionSession.js';

function fixture() {
  const answers = [], errors = [], events = [];
  const rec = {
    start() { events.push('start'); this.onstart?.(); },
    abort() { events.push('abort'); this.onend?.(); },
  };
  const timers = new Map();
  let nextTimer = 0;
  const session = createSpeechSession(rec, {
    onStart: () => events.push('listening'), onText: () => {},
    onFinish: () => events.push('finish'),
    onAnswer: (answer) => { events.push('answer'); answers.push(answer); },
    onError: (error) => errors.push(error),
  }, {
    setTimer: (fn) => { nextTimer += 1; timers.set(nextTimer, fn); return nextTimer; },
    clearTimer: (id) => timers.delete(id),
  });
  const results = [];
  const result = (text, final = false) => {
    const piece = [{ transcript: text }];
    piece.isFinal = final;
    if (results.length && !results[results.length - 1].isFinal) results.pop();
    results.push(piece);
    rec.onresult?.({ results: [...results] });
  };
  // Simula que el niño se quedó callado el tiempo suficiente.
  const silence = () => { const pending = [...timers.values()]; timers.clear(); pending.forEach((fn) => fn()); };
  return { rec, session, result, silence, answers, errors, events };
}

test('La respuesta se envía tras el silencio, cierra el micrófono antes y se envía una sola vez', () => {
  const f = fixture();
  f.session.start();
  f.result('opción B', true);
  assert.deepEqual(f.answers, []);
  f.silence();
  f.silence();
  f.rec.onend();
  assert.deepEqual(f.answers, ['opción B']);
  assert.ok(f.events.indexOf('finish') < f.events.indexOf('answer'));
});

test('Pausar o cambiar de pregunta descarta la transcripción incompleta y resultados tardíos', () => {
  const f = fixture();
  f.session.start();
  f.result('cuatro');
  f.session.cancel();
  f.result('cuatro', true);
  f.rec.onend();
  assert.deepEqual(f.answers, []);
  assert.deepEqual(f.errors, []);
});

test('Un fin normal con transcripción puede entregar la respuesta', () => {
  const f = fixture();
  f.session.start();
  f.result('seis');
  f.rec.onend();
  f.rec.onend();
  assert.deepEqual(f.answers, ['seis']);
});

test('Los errores no envían resultados parciales y permiten un reintento explícito', () => {
  const f = fixture();
  f.session.start();
  f.result('cua');
  f.rec.onerror({ error: 'network' });
  f.rec.onend();
  assert.deepEqual(f.answers, []);
  assert.deepEqual(f.errors, ['network']);
  f.session.start();
  f.result('cuatro', true);
  f.silence();
  assert.deepEqual(f.answers, ['cuatro']);
});

test('La falta de voz informa el error una sola vez; no reinicia en bucle', () => {
  const f = fixture();
  f.session.start();
  f.rec.onend();
  f.rec.onend();
  assert.deepEqual(f.errors, ['no-speech']);
  assert.equal(f.events.filter((event) => event === 'start').length, 1);
});

test('Un inicio rechazado y la limpieza del componente no envían respuestas', () => {
  const f = fixture();
  f.rec.start = () => { throw new Error('Permission denied'); };
  f.session.start();
  assert.deepEqual(f.errors, ['start-failed']);
  f.session.dispose();
  assert.equal(f.rec.onresult, null);
  assert.equal(f.rec.onstart, null);
  assert.deepEqual(f.answers, []);
});

test('Reanudar inmediatamente espera el fin de la escucha anterior', () => {
  const f = fixture();
  f.rec.abort = () => { f.events.push('abort'); };
  f.session.start();
  f.result('parcial');
  f.session.cancel();
  f.session.start();
  assert.equal(f.events.filter((event) => event === 'start').length, 1);
  f.rec.onend();
  assert.equal(f.events.filter((event) => event === 'start').length, 2);
  f.result('ocho', true);
  f.rec.onend();
  assert.deepEqual(f.answers, ['ocho']);
  assert.deepEqual(f.errors, []);
});

test('Las pausas del niño no cortan la respuesta: se juntan los pedazos hasta el silencio', () => {
  const f = fixture();
  f.session.start();
  f.result('eeh la', true);
  f.result('la del');
  f.result('la del sol', true);
  assert.deepEqual(f.answers, []);
  f.silence();
  assert.deepEqual(f.answers, ['eeh la la del sol']);
});
