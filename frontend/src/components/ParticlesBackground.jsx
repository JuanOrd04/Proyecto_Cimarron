import React from 'react';
import { Settings, Sparkles, Hexagon } from 'lucide-react';

const ParticlesBackground = () => {
  return (
    <div className="particles-container">
      {/* Engranajes de Ingeniería Flotantes */}
      <div className="particle particle-gear-1"><Settings size={40} color="rgba(255, 215, 0, 0.15)" /></div>
      <div className="particle particle-gear-2"><Settings size={60} color="rgba(0, 168, 93, 0.15)" /></div>
      <div className="particle particle-gear-3"><Settings size={30} color="rgba(255, 215, 0, 0.15)" /></div>
      
      {/* Átomos / Hexágonos (Tecnología) */}
      <div className="particle particle-hex-1"><Hexagon size={45} color="rgba(0, 168, 93, 0.2)" /></div>
      <div className="particle particle-hex-2"><Hexagon size={35} color="rgba(255, 215, 0, 0.2)" /></div>
      
      {/* Destellos de Magia/Creatividad */}
      <div className="particle particle-spark-1"><Sparkles size={25} color="rgba(255, 255, 255, 0.3)" /></div>
      <div className="particle particle-spark-2"><Sparkles size={20} color="rgba(255, 255, 255, 0.3)" /></div>
      <div className="particle particle-spark-3"><Sparkles size={30} color="rgba(255, 215, 0, 0.3)" /></div>
    </div>
  );
};

export default ParticlesBackground;
