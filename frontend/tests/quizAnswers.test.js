import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { build } from 'esbuild';

const require = createRequire(import.meta.url);
const bundle = await build({ entryPoints: ['src/components/QuizPanel.jsx'], bundle: true, write: false, format: 'cjs', platform: 'node', external: ['react'], logLevel: 'silent' });
const module = { exports: {} };
new Function('require', 'module', 'exports', bundle.outputFiles[0].text)(require, module, module.exports);
const QuizPanel = module.exports.default;
const fixture = JSON.parse(await readFile(new URL('../../backend/tests/fixtures/semantic_questions.json', import.meta.url), 'utf8'))[0];
const game = {
  session_id: 'test-session', grade: 2, subject_label: fixture.subject, total: 5, answered: 0, phase: 'question',
  question: { id: 'test-question', prompt: fixture.prompt, subject: fixture.subject,
    options: fixture.options.map((text, index) => ({ label: String.fromCharCode(65 + index), text })) },
};
const render = (value) => renderToStaticMarkup(React.createElement(QuizPanel, { game: value, busy: false, voiceMode: true, voiceStatus: 'Escuchando', onAnswer() {} }));

test('La pregunta presenta cuatro respuestas accesibles sin párrafos de instrucciones', () => {
  const html = render(game);
  assert.equal((html.match(/aria-label="Opción /g) || []).length, 4);
  for (const option of game.question.options) assert.ok(html.includes(`Opción ${option.label}: ${option.text}`));
  assert.equal((html.match(/class="quiz-question"/g) || []).length, 1);
  assert.ok(!html.includes('micrófono se abrirá'));
  assert.ok(!html.includes('con tus propias palabras'));
});

test('La retroalimentación conserva las opciones y señala la respuesta que informó el servidor', () => {
  const html = render({ ...game, phase: 'feedback', answered: 1,
    feedback: { correct: true, kind: 'correct', text: fixture.explanation, correct_option: game.question.options[0].label } });
  assert.equal((html.match(/aria-label="Opción /g) || []).length, 4);
  assert.equal((html.match(/, respuesta correcta/g) || []).length, 1);
  assert.ok(html.includes('Siguiente'));
  assert.ok(!html.includes('Pasaremos a la siguiente'));
});
