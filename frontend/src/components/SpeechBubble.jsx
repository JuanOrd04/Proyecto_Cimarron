import React, { useState, useEffect } from 'react';

const SpeechBubble = ({ text, isSpeaking, isLoading }) => {
  const [displayedText, setDisplayedText] = useState("");

  useEffect(() => {
    if (!text) {
      setDisplayedText("¡Hola! ¡Presiona el micrófono o una pregunta rápida para conversar conmigo!");
      return;
    }

    if (!isSpeaking) {
      setDisplayedText(text); // Mostrar todo cuando no está hablando (o al terminar)
      return;
    }

    // Efecto Karaoke simulado (revelar palabras progresivamente mientras habla)
    const words = text.split(" ");
    let currentWordIndex = 0;
    
    // Estimación: 190 palabras por minuto (aprox 315 ms por palabra)
    const msPerWord = 315; 
    
    setDisplayedText(""); // Reiniciar

    const intervalId = setInterval(() => {
      if (currentWordIndex < words.length) {
        setDisplayedText(words.slice(0, currentWordIndex + 1).join(" "));
        currentWordIndex++;
      } else {
        clearInterval(intervalId);
      }
    }, msPerWord);

    return () => clearInterval(intervalId);
  }, [text, isSpeaking]);

  return (
    <div className="speech-bubble-wrapper">
      <div className={`speech-bubble glass-panel ${isSpeaking ? 'active-speaking' : ''}`}>
        <div className="speech-bubble-badge">
          <span> mascota UABC INGENIERÍA </span>
        </div>
        
        {isLoading ? (
          <div className="loading-dots">
            <span>¡Pensando respuesta brillante!</span>
            <div className="dots-flex">
              <span className="dot dot1">•</span>
              <span className="dot dot2">•</span>
              <span className="dot dot3">•</span>
            </div>
          </div>
        ) : (
          <p className="speech-bubble-text karaoke-text">
            {displayedText}
            {isSpeaking && <span className="karaoke-cursor"></span>}
          </p>
        )}

        {/* Tail / Pico de la burbuja */}
        <div className="speech-bubble-tail" />
      </div>
    </div>
  );
};

export default SpeechBubble;
