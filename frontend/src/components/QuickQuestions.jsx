import React, { useState } from 'react';
import Sparkles from 'lucide-react/dist/esm/icons/sparkles';
import GraduationCap from 'lucide-react/dist/esm/icons/graduation-cap';
import HardHat from 'lucide-react/dist/esm/icons/hard-hat';
import Bot from 'lucide-react/dist/esm/icons/bot';
import Plane from 'lucide-react/dist/esm/icons/plane';
import Cpu from 'lucide-react/dist/esm/icons/cpu';
import Zap from 'lucide-react/dist/esm/icons/zap';
import ChevronDown from 'lucide-react/dist/esm/icons/chevron-down';
import { playHover } from '../utils/sfx';

const PRESET_QUESTIONS = [
  { text: "¿A qué se dedica un ingeniero?", icon: GraduationCap },
  { text: "¿Cómo se construye un puente moderno?", icon: HardHat },
  { text: "¿Qué proyectos de robótica desarrollan en la UABC?", icon: Bot },
  { text: "¿Cómo logran volar los aviones?", icon: Plane },
  { text: "¿Cómo funciona internamente una computadora?", icon: Cpu },
  { text: "¿Qué carreras ofrece la Facultad de Ingeniería?", icon: Zap }
];

const QuickQuestions = ({ onSelectQuestion, disabled, sfxEnabled }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const toggleAccordion = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <div className="quick-questions-wrapper glass-panel">
      <div 
        className="quick-questions-header" 
        onClick={toggleAccordion}
        title={isExpanded ? "Ocultar preguntas" : "Mostrar preguntas"}
      >
        <div className="header-left">
          <Sparkles size={20} color="#FFD700" className="animate-spin-slow" />
          <span>Preguntas Rápidas</span>
        </div>
        <ChevronDown 
          size={24} 
          className={`chevron-icon ${isExpanded ? 'open' : ''}`} 
        />
      </div>
      
      <div className={`quick-questions-content ${isExpanded ? 'open' : ''}`}>
        <div className="quick-questions-grid">
          {PRESET_QUESTIONS.map((item, index) => {
            const Icon = item.icon;
            return (
              <button
                key={index}
                onClick={() => {
                  onSelectQuestion(item.text);
                  setIsExpanded(false); // Opcional: Cerrar al seleccionar
                }}
                onMouseEnter={() => { if (sfxEnabled && !disabled) playHover(); }}
                disabled={disabled}
                className="quick-question-card"
              >
                <div className="card-icon-wrapper">
                  <Icon size={24} className="card-icon" />
                </div>
                <span className="card-text">{item.text}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default QuickQuestions;
