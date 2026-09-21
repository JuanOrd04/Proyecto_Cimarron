import React, { useState, useRef, useEffect } from 'react';
import Volume2 from 'lucide-react/dist/esm/icons/volume-2';
import VolumeX from 'lucide-react/dist/esm/icons/volume-x';
import CimarronAvatar from './components/CimarronAvatar';
import SpeechBubble from './components/SpeechBubble';
import SpeechButton from './components/SpeechButton';
import QuickQuestions from './components/QuickQuestions';
import ParticlesBackground from './components/ParticlesBackground';
import './App.css';

const BACKEND_URL = "http://127.0.0.1:8000/chat";

function App() {
  const [responseText, setResponseText] = useState("¡Hola! Bienvenido a la Facultad de Ingeniería de la UABC. ¿En qué te puedo ayudar hoy?");
  const [isLoading, setIsLoading] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [mouthFrame, setMouthFrame] = useState(0); // 0 a 3 para 4 poses
  const [isListening, setIsListening] = useState(false);
  const [sfxEnabled, setSfxEnabled] = useState(true);
  const [showBubble, setShowBubble] = useState(true);

  const audioRef = useRef(null);
  const mouthIntervalRef = useRef(null);
  const abortControllerRef = useRef(null); // Para cancelar la petición al backend

  useEffect(() => {
    return () => {
      if (mouthIntervalRef.current) clearInterval(mouthIntervalRef.current);
    };
  }, []);

  // Efecto para mutear/desmutear en tiempo real si el usuario cambia el volumen mientras el avatar habla
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.muted = !sfxEnabled;
    }
  }, [sfxEnabled]);

  const playAudioWithMouthSync = (audioBase64) => {
    if (!audioBase64) return;

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (mouthIntervalRef.current) {
      clearInterval(mouthIntervalRef.current);
    }

    try {
      const audio = new Audio(audioBase64);
      audio.muted = !sfxEnabled; // Aplica el estado actual de volumen
      audioRef.current = audio;

      audio.onplay = () => {
        setIsSpeaking(true);
        mouthIntervalRef.current = setInterval(() => {
          setMouthFrame((prev) => (prev + 1) % 4);
        }, 160); // Ajuste ligero para ver bien ambas poses
      };

      audio.onended = () => {
        setIsSpeaking(false);
        setMouthFrame(0);
        if (mouthIntervalRef.current) clearInterval(mouthIntervalRef.current);
      };

      audio.onerror = (e) => {
        console.warn("No se pudo reproducir audio sintetizado:", e);
        setIsSpeaking(false);
        setMouthFrame(0);
        if (mouthIntervalRef.current) clearInterval(mouthIntervalRef.current);
      };

      audio.play().catch((err) => {
        console.warn("Autoplay bloqueado:", err);
        setIsSpeaking(false);
        setMouthFrame(0);
      });
    } catch (err) {
      console.error("Error Audio:", err);
    }
  };

  const handleSendMessage = async (userMessage) => {
    if (!userMessage || isLoading) return;

    setIsLoading(true);
    if (audioRef.current) audioRef.current.pause();
    if (mouthIntervalRef.current) clearInterval(mouthIntervalRef.current);
    setIsSpeaking(false);
    setMouthFrame(0);

    // Cancelar cualquier petición anterior
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(BACKEND_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      setResponseText(data.response);
      setIsLoading(false);

      if (data.audio) {
        playAudioWithMouthSync(data.audio);
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('Petición cancelada por el usuario');
        return;
      }
      console.error("Error backend:", error);
      setResponseText("¡Ups! Parece que mi servidor local está descansando. ¡Revisa que uvicorn esté corriendo en http://127.0.0.1:8000!");
      setIsLoading(false);
    }
  };

  const handleStop = () => {
    // 1. Detener petición de red si está pensando
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    // 2. Detener audio si está hablando
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    if (mouthIntervalRef.current) clearInterval(mouthIntervalRef.current);
    
    setIsLoading(false);
    setIsSpeaking(false);
    setMouthFrame(0);
  };

  return (
    <>
      <ParticlesBackground />
      <div className="app-container">
        
        {/* Botón de Volumen (Movido a la esquina superior derecha general) */}
        <button 
          className="sfx-toggle-btn" 
          onClick={() => setSfxEnabled(!sfxEnabled)}
          title={sfxEnabled ? "Silenciar Efectos (SFX)" : "Activar Efectos (SFX)"}
        >
          {sfxEnabled ? <Volume2 size={24} /> : <VolumeX size={24} color="#EF4444" />}
        </button>

        <header className="app-header glass-panel">
          <div className="header-badge">Universidad Autónoma de Baja California</div>
          <h1 className="app-title">Asistente Interactivo "Cimarrón"</h1>
          {/* El subtítulo ha sido eliminado a petición del usuario */}
        </header>

        <main className="main-stage">
          <CimarronAvatar 
            isSpeaking={isSpeaking} 
            isThinking={isLoading}
            isListening={isListening}
            mouthFrame={mouthFrame} 
            onAvatarClick={() => setShowBubble(!showBubble)}
            sfxEnabled={sfxEnabled}
          />
          <SpeechBubble 
            text={responseText} 
            isSpeaking={isSpeaking} 
            isLoading={isLoading}
            isVisible={showBubble}
          />
        </main>

        <section className="controls-section">
          <QuickQuestions onSelectQuestion={handleSendMessage} disabled={isLoading || isSpeaking} />
          <SpeechButton
            onSpeechResult={handleSendMessage}
            onStop={handleStop}
            isLoading={isLoading}
            isSpeaking={isSpeaking}
            disabled={isLoading || isSpeaking}
            isListening={isListening}
            setIsListening={setIsListening}
            sfxEnabled={sfxEnabled}
          />
        </section>

      </div>
    </>
  );
}

export default App;
