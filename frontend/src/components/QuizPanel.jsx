import React, { useState } from 'react';
import Gamepad2 from 'lucide-react/dist/esm/icons/gamepad-2';
import Trophy from 'lucide-react/dist/esm/icons/trophy';
import ArrowRight from 'lucide-react/dist/esm/icons/arrow-right';

const SUBJECTS = [
  ['mixto', 'Un poco de todo'],
  ['matematicas', 'Matemáticas'],
  ['ciencias_naturales', 'Ciencias naturales'],
  ['geografia', 'Geografía'],
  ['biologia', 'Biología'],
  ['espanol', 'Español'],
];

export default function QuizPanel({ game, setupOpen, busy, error, onOpen, onStart, onAnswer, onNext, onEnd, voiceMode, voiceStatus, onToggleVoice }) {
  const [grade, setGrade] = useState(1);
  const [subject, setSubject] = useState('mixto');
  const finished = game?.phase === 'finished';

  return (
    <section className="quiz-panel glass-panel" aria-label="Juego de primaria">
      <div className="quiz-header">
        <div className="quiz-heading">
          <span className="quiz-icon"><Gamepad2 size={26} /></span>
          <div><h2>Aprende jugando</h2><p>Cinco preguntas. ¡Mucho por descubrir!</p></div>
        </div>
        {!game && !setupOpen && (
          <button className="quiz-primary" onClick={onOpen} disabled={busy}>Iniciar juego <ArrowRight size={18} /></button>
        )}
        {(game || setupOpen) && <button className="quiz-exit" onClick={onEnd}>Volver al chat</button>}
      </div>

      {setupOpen && !game && (
        <form className="quiz-setup" onSubmit={(event) => { event.preventDefault(); onStart({ grade, subject }); }}>
          <p className="quiz-welcome">¡Hola! Soy el Cimarrón. ¿Qué te gustaría practicar?</p>
          <div className="quiz-fields">
            <label>¿En qué grado de primaria estás?
              <select value={grade} onChange={(event) => setGrade(Number(event.target.value))} disabled={busy}>
                {[1, 2, 3, 4, 5, 6].map((number) => <option key={number} value={number}>{number}.º de primaria</option>)}
              </select>
            </label>
            <label>Elige una materia
              <select value={subject} onChange={(event) => setSubject(event.target.value)} disabled={busy}>
                {SUBJECTS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
          </div>
          <button type="submit" className="quiz-primary" disabled={busy}>{busy ? 'Preparando el juego…' : '¡Vamos a jugar!'}</button>
        </form>
      )}

      {game && (
        <div className="quiz-content">
          {!finished && <div className="quiz-voice-controls">
            <p role="status">{voiceMode ? `Modo de voz · ${voiceStatus}` : 'Modo de voz pausado. Puedes usar los botones o escribir.'}</p>
            <button className="quiz-exit" onClick={onToggleVoice} aria-pressed={voiceMode}>{voiceMode ? 'Pausar voz' : 'Reanudar voz'}</button>
          </div>}
          <div className="quiz-meta">
            <span>{game.grade}.º de primaria · {game.subject_label}</span>
            <span>{finished ? 'Ronda completada' : `Pregunta ${Math.min(game.answered + (game.phase === 'question' ? 1 : 0), game.total)} de ${game.total}`}</span>
          </div>
          <div className="quiz-progress" aria-label={`${game.answered} de ${game.total} preguntas respondidas`}>
            {Array.from({ length: game.total }, (_, index) => <span key={index} className={`quiz-step ${index < game.answered ? 'completed' : ''} ${index === game.answered && game.phase === 'question' ? 'current' : ''}`}>{index + 1}</span>)}
          </div>

          {game.phase === 'question' && (
            <>
              <span className="quiz-subject">{game.question.subject}</span>
              <h3 className="quiz-question">{game.question.prompt}</h3>
              <div className="quiz-options">
                {game.question.options.map((option) => (
                  <button key={option.label} className="quiz-option" disabled={busy} onClick={() => onAnswer(option.text)}>
                    <span className="quiz-option-letter">{option.label}</span><span>{option.text}</span>
                  </button>
                ))}
              </div>
              <p className="quiz-hint">{voiceMode ? 'Cuando termine de hablar, el micrófono se abrirá solo. ' : ''}Cuéntame lo que piensas con tus propias palabras. También puedes elegir una opción o escribir abajo.</p>
            </>
          )}

          {game.feedback && (
            <div className={`quiz-feedback ${game.feedback.correct ? 'correct' : 'learning'}`} role="status">
              <strong>{game.feedback.kind === 'partial' ? '¡Vamos por buen camino!' : game.feedback.kind === 'unclear' ? 'Cuéntame un poco más' : game.feedback.correct ? '¡Respuesta correcta!' : '¡Seguimos aprendiendo!'}</strong>
              <p>{game.feedback.text}</p>
            </div>
          )}

          {game.phase === 'feedback' && <>
            {voiceMode && <p className="quiz-hint">Pasaremos a la siguiente pregunta al terminar la explicación.</p>}
            <button className="quiz-primary" onClick={onNext} disabled={busy}>{busy ? 'Escucha la explicación…' : 'Siguiente pregunta'} <ArrowRight size={18} /></button>
          </>}

          {finished && (
            <div className="quiz-result">
              <Trophy size={38} aria-hidden="true" />
              <h3>¡Lo lograste!</h3>
              <p className="quiz-score">{game.score}<span> / {game.total}</span></p>
              <p>Preguntas acertadas. ¡Cada intento te ayuda a aprender!</p>
              <button className="quiz-primary" onClick={onOpen} disabled={busy}>Jugar otra vez</button>
            </div>
          )}
        </div>
      )}
      {error && <p className="quiz-error" role="alert">{error}</p>}
    </section>
  );
}
