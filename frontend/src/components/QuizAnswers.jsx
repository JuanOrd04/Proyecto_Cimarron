import React, { useState } from 'react';

export default function QuizAnswers({ question, feedback, busy, onAnswer }) {
  const [seleccion, actualizarSeleccion] = useState(null);
  const respondida = typeof feedback?.correct === 'boolean';
  const letraSeleccionada = seleccion?.idPregunta === question.id && (busy || respondida) ? seleccion.letra : null;

  return (
    <div className="quiz-options" role="group" aria-label="Respuestas" aria-busy={busy}>
      {question.options.map((opcion, indice) => {
        const esCorrecta = respondida && feedback.correct_option === opcion.label;
        const esIncorrecta = respondida && !esCorrecta && letraSeleccionada === opcion.label;
        const estadoVisual = esCorrecta ? 'correct' : esIncorrecta ? 'incorrect' : respondida ? 'muted' : letraSeleccionada === opcion.label ? 'selected' : '';
        const estadoAccesible = esCorrecta ? ', respuesta correcta' : esIncorrecta ? ', respuesta incorrecta' : '';
        return (
          <button
            key={opcion.label}
            className={`quiz-option quiz-option-${indice} ${estadoVisual}`}
            disabled={busy || respondida}
            aria-label={`Opción ${opcion.label}: ${opcion.text}${estadoAccesible}`}
            aria-pressed={letraSeleccionada === opcion.label}
            onClick={() => { actualizarSeleccion({ idPregunta: question.id, letra: opcion.label }); onAnswer(opcion.text); }}
          >
            <span className="quiz-option-letter" aria-hidden="true">{opcion.label}</span>
            <span className="quiz-option-text">{opcion.text}</span>
            {(esCorrecta || esIncorrecta) && <span className="quiz-option-result" aria-hidden="true">{esCorrecta ? '✓' : '×'}</span>}
          </button>
        );
      })}
    </div>
  );
}
