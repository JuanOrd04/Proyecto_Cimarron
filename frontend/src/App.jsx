import React, { useState, useRef, useEffect } from 'react';
import { Volume2, VolumeX } from 'lucide-react';
import CimarronAvatar from './components/CimarronAvatar';
import SpeechBubble from './components/SpeechBubble';
import SpeechButton from './components/SpeechButton';
import QuickQuestions from './components/QuickQuestions';
import ParticlesBackground from './components/ParticlesBackground';
import './App.css';

const BACKEND_URL = "http://127.0.0.1:8000/chat";

function App() {
  const [responseText, setResponseText] = useState("¡Hola explorador! ¡Bienvenido a la Facultad de Ingeniería de la UABC! ¿Qué te gustaría descubrir hoy?");
  const [isLoading, setIsLoading] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [mouthFrame, setMouthFrame] = useState(0); // 0 a 3 para 4 poses
  const [isListening, setIsListening] = useState(false);
  const [sfxEnabled, setSfxEnabled] = useState(true);
  const [showBubble, setShowBubble] = useState(true);

  const audioRef = useRef(null);
  const mouthIntervalRef = useRef(null);

  useEffect(() => {
    return () => {
      if (mouthIntervalRef.current) clearInterval(mouthIntervalRef.current);
    };
  }, []);

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

    try {
      const response = await fetch(BACKEND_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      setResponseText(data.response);
      setIsLoading(false);

      if (data.audio) {
        playAudioWithMouthSync(data.audio);
      }
    } catch (error) {
      console.error("Error backend:", error);
      setResponseText("¡Ups! Parece que mi servidor local está descansando. ¡Revisa que uvicorn esté corriendo en http://127.0.0.1:8000!");
      setIsLoading(false);
    }
  };

  return (
    <>
      <ParticlesBackground />
      <div className="app-container">
        <header className="app-header glass-panel">
          <div className="header-badge">Universidad Autónoma de Baja California</div>
          <h1 className="app-title">Asistente Interactivo "Cimarrón"</h1>
          <p className="app-subtitle">Facultad de Ingeniería • Visitas de Primaria y Secundaria</p>
          
          <button 
            className="sfx-toggle-btn" 
            onClick={() => setSfxEnabled(!sfxEnabled)}
            title={sfxEnabled ? "Silenciar Efectos (SFX)" : "Activar Efectos (SFX)"}
          >
            {sfxEnabled ? <Volume2 size={20} /> : <VolumeX size={20} color="#EF4444" />}
          </button>
        </header>

        <main className="main-stage">
          <CimarronAvatar
            isSpeaking={isSpeaking}
            mouthFrame={mouthFrame}
            sfxEnabled={sfxEnabled}
            isThinking={isLoading || isListening}
            onAvatarClick={() => setShowBubble(!showBubble)}
          />
          <SpeechBubble
            text={responseText}
            isSpeaking={isSpeaking}
            isLoading={isLoading}
            isVisible={showBubble}
          />
        </main>

        <section className="controls-section">
          <QuickQuestions
            onSelectQuestion={handleSendMessage}
            disabled={isLoading || isSpeaking}
            sfxEnabled={sfxEnabled}
          />
          <SpeechButton
            onSpeechResult={handleSendMessage}
            disabled={isLoading || isSpeaking}
            isListening={isListening}
            setIsListening={setIsListening}
            sfxEnabled={sfxEnabled}
          />
        </section>

        <footer className="app-footer glass-panel">
          <p>🟢</p>
        </footer>
      </div>
    </>
  );
}

export default App;
