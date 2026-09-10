import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Send } from 'lucide-react';
import { playChimeOn, playChimeOff } from '../utils/sfx';

const SpeechButton = ({ onSpeechResult, disabled, isListening, setIsListening, sfxEnabled }) => {
  const [textInput, setTextInput] = useState('');
  const [recognition, setRecognition] = useState(null);
  const [supportsSpeech, setSupportsSpeech] = useState(true);
  const [micVolume, setMicVolume] = useState(0);
  
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const animationFrameRef = useRef(null);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = false;
      rec.lang = 'es-MX';

      rec.onstart = () => {
        setIsListening(true);
        startVolumeMeter();
      };

      rec.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript && onSpeechResult) {
          onSpeechResult(transcript);
        }
      };

      rec.onerror = (event) => {
        console.warn('Error en Web Speech API:', event.error);
        setIsListening(false);
        stopVolumeMeter();
      };

      rec.onend = () => {
        setIsListening(false);
        stopVolumeMeter();
      };

      setRecognition(rec);
    } else {
      setSupportsSpeech(false);
    }

    return () => stopVolumeMeter();
  }, [onSpeechResult, setIsListening]);

  const startVolumeMeter = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = audioCtx;
      
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;
      
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      
      const updateVolume = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const average = sum / dataArray.length;
        setMicVolume(average); // 0 a 255
        
        animationFrameRef.current = requestAnimationFrame(updateVolume);
      };
      
      updateVolume();
    } catch (err) {
      console.warn("No se pudo acceder al micrófono para el visualizador:", err);
    }
  };

  const stopVolumeMeter = () => {
    if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }
    setMicVolume(0);
  };

  const toggleMic = () => {
    if (!recognition) return;
    if (isListening) {
      if (sfxEnabled) playChimeOff();
      recognition.stop();
    } else {
      if (sfxEnabled) playChimeOn();
      try {
        recognition.start();
      } catch (err) {
        console.error('Error al iniciar micrófono:', err);
      }
    }
  };

  const handleSubmitText = (e) => {
    e.preventDefault();
    if (textInput.trim() && onSpeechResult) {
      onSpeechResult(textInput.trim());
      setTextInput('');
    }
  };

  // Calcular barras de audio dinámicas
  const bars = Array.from({ length: 5 }).map((_, i) => {
    const height = Math.max(6, (micVolume / 255) * 32 * (1 - (Math.abs(2 - i) * 0.2)));
    return height;
  });

  return (
    <div className="speech-button-container glass-panel">
      <form onSubmit={handleSubmitText} className="input-form">
        <input
          type="text"
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder="Escribe tu pregunta aquí..."
          disabled={disabled || isListening}
          className="chat-text-input"
        />

        <button
          type="submit"
          disabled={disabled || !textInput.trim() || isListening}
          className="send-button"
          title="Enviar mensaje"
        >
          <Send size={26} />
        </button>

        {supportsSpeech && (
          <button
            type="button"
            onClick={toggleMic}
            disabled={disabled}
            className={`mic-button ${isListening ? 'listening-active' : ''}`}
            title={isListening ? "Escuchando... Haz clic para detener" : "Haz clic y habla"}
          >
            {isListening ? (
              <div className="mic-visualizer">
                {bars.map((h, i) => (
                  <div key={i} className="mic-bar" style={{ height: `${h}px` }} />
                ))}
              </div>
            ) : (
              <><Mic size={28} /><span className="mic-label">Hablar</span></>
            )}
          </button>
        )}
      </form>
    </div>
  );
};

export default SpeechButton;
