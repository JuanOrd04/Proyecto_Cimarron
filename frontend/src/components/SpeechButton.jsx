import React, { useState, useEffect, useRef } from 'react';
import Mic from 'lucide-react/dist/esm/icons/mic';
import Send from 'lucide-react/dist/esm/icons/send';
import Square from 'lucide-react/dist/esm/icons/square';
import { playChimeOn, playChimeOff } from '../utils/sfx';
import { createSpeechSession, speechErrorMessage } from '../utils/speechRecognitionSession';

const SpeechButton = ({ onSpeechResult, disabled, isListening, setIsListening, sfxEnabled, onStop, isLoading, isSpeaking, autoListen = false, autoListenKey = 0, onPauseAuto, onVoiceError, showVoiceError = true, placeholderText = 'Escribe tu pregunta aquí...', compact = false }) => {
  const [textInput, setTextInput] = useState('');
  const [session, setSession] = useState(null);
  const [voiceError, setVoiceError] = useState('');
  const voiceErrorRef = useRef(onVoiceError);
  voiceErrorRef.current = onVoiceError;
  const autoStartedRef = useRef(false);
  const lastAutoAttemptRef = useRef(null);
  const [supportsSpeech, setSupportsSpeech] = useState(true);
  const [micVolume, setMicVolume] = useState(0);
  
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const animationFrameRef = useRef(null);
  const volumeRequestRef = useRef(0);

  const onSpeechResultRef = useRef(onSpeechResult);
  useEffect(() => {
    onSpeechResultRef.current = onSpeechResult;
  }, [onSpeechResult]);


  // Limpiar el recuadro de texto cuando el Cimarrón termina de responder
  const prevLoadingRef = useRef(isLoading);
  useEffect(() => {
    if (prevLoadingRef.current && !isLoading) {
      setTextInput('');
    }
    prevLoadingRef.current = isLoading;
  }, [isLoading]);

  useEffect(() => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setSupportsSpeech(false);
      const message = speechErrorMessage('unsupported');
      setVoiceError(message);
      voiceErrorRef.current?.(message);
      return;
    }
    const rec = new Recognition();
    rec.continuous = true; // La sesión decide cuándo terminó el niño, por silencio
    rec.interimResults = true;
    rec.lang = 'es-MX';
    const activeSession = createSpeechSession(rec, {
      onStart: () => { setIsListening(true); startVolumeMeter(); },
      onText: setTextInput,
      onAnswer: (answer) => onSpeechResultRef.current?.(answer),
      onFinish: () => { setIsListening(false); stopVolumeMeter(); },
      onError: (error) => {
        const message = speechErrorMessage(error);
        setVoiceError(message);
        voiceErrorRef.current?.(message);
      },
    });
    setSession(activeSession);
    return () => {
      activeSession.dispose();
      stopVolumeMeter();
      setIsListening(false);
    };
  }, [setIsListening]);

  useEffect(() => {
    if (!session) return;
    if (disabled || (autoStartedRef.current && !autoListen)) {
      autoStartedRef.current = false;
      session.cancel();
    }
    if (autoListen && !disabled && lastAutoAttemptRef.current !== autoListenKey) {
      lastAutoAttemptRef.current = autoListenKey;
      autoStartedRef.current = true;
      setVoiceError('');
      setTextInput('');
      session.start();
    }
  }, [session, disabled, autoListen, autoListenKey]);

  const startVolumeMeter = async () => {
    const request = ++volumeRequestRef.current;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (request !== volumeRequestRef.current) {
        stream.getTracks().forEach(track => track.stop());
        return;
      }
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
    volumeRequestRef.current += 1;
    if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    animationFrameRef.current = null;
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    if (audioContextRef.current) {
      if (audioContextRef.current.state !== 'closed') audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    setMicVolume(0);
  };

  const toggleMic = () => {
    if (!session) return;
    if (isListening) {
      if (sfxEnabled) playChimeOff();
      session.cancel();
      autoStartedRef.current = false;
      if (autoListen) onPauseAuto?.();
    } else {
      setTextInput('');
      setVoiceError('');
      // La escucha automática empieza sin campanilla para no transcribirla.
      if (sfxEnabled) playChimeOn();
      session.start();
    }
  };

  const handleSubmitText = (e) => {
    e.preventDefault();
    if (disabled || isListening) return;
    if (textInput.trim() && onSpeechResultRef.current) {
      session?.cancel();
      onSpeechResultRef.current(textInput.trim());
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
          placeholder={isListening ? compact ? 'Escuchando…' : '🎙️ Escuchando... Te escucho...' : placeholderText}
          aria-label={placeholderText}
          disabled={disabled}
          readOnly={isListening}
          className={`chat-text-input ${isListening ? 'input-listening' : ''}`}
        />

        {(isLoading || isSpeaking) ? (
          <button
            type="button"
            onClick={onStop}
            className="stop-button"
            title="Detener respuesta"
          >
            <Square size={24} fill="currentColor" />
          </button>
        ) : (
          <>
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
          </>
        )}
      </form>
      {showVoiceError && voiceError && <p className="speech-error" role="status">{voiceError}</p>}
    </div>
  );
};

export default SpeechButton;
