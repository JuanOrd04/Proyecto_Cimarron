import test from 'node:test';
import assert from 'node:assert/strict';
import { createSpeechSession } from '../src/utils/speechRecognitionSession.js';

function fixture() {
  const answers = [], errors = [], events = [];
  const rec = {
    start() { events.push('start'); this.onstart?.(); },
    abort() { events.push('abort'); this.onend?.(); },
  };
  const session = createSpeechSession(rec, {
    onStart: () => events.push('listening'), onText: () => {},
    onFinish: () => events.push('finish'),
    onAnswer: (answer) => { events.push('answer'); answers.push(answer); },
    onError: (error) => errors.push(error),
  });
  const result = (text, final = false) => {
    const piece = [{ transcript: text }];
    piece.isFinal = final;
    rec.onresult?.({ results: [piece] });
  };
  return { rec, session, result, answers, errors, events };
}

test('Una respuesta final cierra el micrófono antes de enviar y se envía una sola vez', () => {
  const f = fixture();
  f.session.start();
  f.result('opción B', true);
  f.result('opción B', true);
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
