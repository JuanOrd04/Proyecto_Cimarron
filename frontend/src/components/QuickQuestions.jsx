import React from 'react';
import { Sparkles, Bot, HardHat, Plane, Cpu, GraduationCap, Zap } from 'lucide-react';
import { playHover } from '../utils/sfx';

const PRESET_QUESTIONS = [
  { text: "¿Qué hace un ingeniero?", icon: GraduationCap },
  { text: "¿Cómo construyen un puente gigante?", icon: HardHat },
  { text: "¿Cómo funcionan los robots de la UABC?", icon: Bot },
  { text: "¿Por qué pueden volar los aviones?", icon: Plane },
  { text: "¿Cómo funcionan las computadoras por dentro?", icon: Cpu },
  { text: "¿Qué puedo aprender en la Facultad de Ingeniería?", icon: Zap }
];

const QuickQuestions = ({ onSelectQuestion, disabled, sfxEnabled }) => {
  return (
    <div className="quick-questions-wrapper glass-panel">
      <div className="quick-questions-header">
        <Sparkles size={20} color="#FFD700" className="animate-spin-slow" />
        <span>Preguntas Rápidas:</span>
      </div>
      <div className="quick-questions-grid">
        {PRESET_QUESTIONS.map((item, index) => {
          const Icon = item.icon;
          return (
            <button
              key={index}
              onClick={() => onSelectQuestion(item.text)}
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
  );
};

export default QuickQuestions;
