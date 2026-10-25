import React, { useEffect, useState } from 'react';
import { observarPreparacionQuiz } from '../quizPreparation';
import Gamepad2 from 'lucide-react/dist/esm/icons/gamepad-2';
import Trophy from 'lucide-react/dist/esm/icons/trophy';
import ArrowRight from 'lucide-react/dist/esm/icons/arrow-right';
import Mic from 'lucide-react/dist/esm/icons/mic';
import MicOff from 'lucide-react/dist/esm/icons/mic-off';
import QuizAnswers from './QuizAnswers';

const SUBJECTS = [
  ['mixto', 'Un poco de todo'],
  ['matematicas', 'Matemáticas'],
  ['ciencias_naturales', 'Ciencias naturales'],
  ['geografia', 'Geografía'],
  ['biologia', 'Biología'],
  ['espanol', 'Español'],
];

export default function QuizPanel({ game, setupOpen, busy, error, onOpen, onStart, onAnswer, onNext, onEnd, voiceMode, voiceStatus, onToggleVoice, apiBaseUrl, avatar }) {
  const [grade, setGrade] = useState(1);
  const [subject, setSubject] = useState('mixto');
  const [preparacion, actualizarPreparacion] = useState(null);
  const [errorPreparacion, actualizarErrorPreparacion] = useState('');
  const [intentoPreparacion, actualizarIntentoPreparacion] = useState(0);
  const finished = game?.phase === 'finished';

  useEffect(() => {
    if (!setupOpen || game) return;
    actualizarPreparacion(null);
    actualizarErrorPreparacion('');
    return observarPreparacionQuiz({ apiBaseUrl, grade, subject, onUpdate: actualizarPreparacion, onError: actualizarErrorPreparacion });
  }, [setupOpen, game?.session_id, grade, subject, apiBaseUrl, intentoPreparacion]);

  return (
    <section className="quiz-panel glass-panel" aria-label="Juego de primaria">
      <div className="quiz-header">
        <div className="quiz-heading">
          <span className="quiz-icon"><Gamepad2 size={26} /></span>
          <h2>{game && !finished ? game.question.subject : 'Aprende jugando'}</h2>
        </div>
        {!game && !setupOpen && (
          <button className="quiz-primary" onClick={onOpen} disabled={busy}>Iniciar juego <ArrowRight size={18} /></button>
        )}
        {(game || setupOpen) && <div className="quiz-actions">
          {game && !finished && <>
            <span className={`quiz-voice-status ${voiceMode ? 'active' : ''}`} role="status"><span className="quiz-status-dot" aria-hidden="true" />{voiceMode ? voiceStatus : 'Voz pausada'}</span>
            <button className="quiz-voice-toggle" onClick={onToggleVoice} aria-pressed={voiceMode} aria-label={voiceMode ? 'Pausar voz automática' : 'Reanudar voz automática'} title={voiceMode ? 'Pausar voz' : 'Reanudar voz'}>{voiceMode ? <Mic size={20} /> : <MicOff size={20} />}</button>
          </>}
          <button className="quiz-exit" onClick={onEnd}>Volver al chat</button>
        </div>}
      </div>

      {setupOpen && !game && (
        <div className="quiz-setup-layout">
          {avatar && <div className="quiz-setup-mascot">{avatar}</div>}
          <form className="quiz-setup" onSubmit={(event) => { event.preventDefault(); onStart({ grade, subject }); }}>
            <div className="quiz-setup-welcome">
              <h3>¡Vamos a jugar!</h3>
              <p>Elige tu grado y la materia que quieres practicar.</p>
            </div>
            <div className="quiz-fields">
              <label>Grado
                <select value={grade} onChange={(event) => setGrade(Number(event.target.value))} disabled={busy}>
                  {[1, 2, 3, 4, 5, 6].map((number) => <option key={number} value={number}>{number}.º de primaria</option>)}
                </select>
              </label>
              <label>Materia
                <select value={subject} onChange={(event) => setSubject(event.target.value)} disabled={busy}>
                  {SUBJECTS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </label>
            </div>
            <div className="quiz-preparation" role="status">
              <span>{preparacion?.state === 'ready' ? 'Listo' : errorPreparacion ? 'Preparación pendiente' : 'Preparando'}</span>
              <span>{preparacion?.ready || 0} / {preparacion?.required || 5}</span>
            </div>
            {errorPreparacion && <p role="alert">{errorPreparacion} <button type="button" className="quiz-exit" onClick={() => actualizarIntentoPreparacion((intento) => intento + 1)}>Reintentar</button></p>}
            <button type="submit" className="quiz-primary" disabled={busy || preparacion?.state !== 'ready'}>{busy ? 'Comenzando…' : 'Comenzar'}</button>
          </form>
        </div>
      )}

      {game && (
        <div className="quiz-content">
          <div className="quiz-meta">
            <span>{game.grade}.º de primaria</span>
            <span>{finished ? 'Resultado' : `${Math.min(game.answered + (game.phase === 'question' ? 1 : 0), game.total)} / ${game.total}`}</span>
          </div>
          <div className="quiz-progress" aria-label={`${game.answered} de ${game.total} preguntas respondidas`}>
            {Array.from({ length: game.total }, (_, index) => <span key={index} className={`quiz-step ${index < game.answered ? 'completed' : ''} ${index === game.answered && game.phase === 'question' ? 'current' : ''}`} />)}
          </div>

          {!finished && (
            <>
              <div className="quiz-presenter">
                {avatar && <div className="quiz-mascot">{avatar}</div>}
                <h3 className="quiz-question">{game.question.prompt}</h3>
              </div>
              <QuizAnswers question={game.question} feedback={game.feedback} busy={busy} onAnswer={onAnswer} />
            </>
          )}

          {game.feedback && (
            <div className={`quiz-feedback ${game.feedback.correct ? 'correct' : 'learning'}`} role="status">
              <strong>{game.feedback.kind === 'partial' || game.feedback.kind === 'unclear' ? 'Un poco más…' : game.feedback.correct ? '¡Correcto!' : 'Buen intento'}</strong>
              <p>{game.feedback.text}</p>
            </div>
          )}

          {game.phase === 'feedback' && <>
            <button className="quiz-primary quiz-next" onClick={onNext} disabled={busy}>{busy ? 'Cargando…' : 'Siguiente'} <ArrowRight size={18} /></button>
          </>}

          {finished && (
            <div className="quiz-presenter">
              {avatar && <div className="quiz-mascot">{avatar}</div>}
              <div className="quiz-result">
                <Trophy size={38} aria-hidden="true" />
                <h3>¡Ronda completa!</h3>
                <p className="quiz-score">{game.score}<span> / {game.total}</span></p>
                <button className="quiz-primary" onClick={onOpen} disabled={busy}>Jugar otra vez</button>
              </div>
            </div>
          )}
        </div>
      )}
      {error && <p className="quiz-error" role="alert">{error}</p>}
    </section>
  );
}
