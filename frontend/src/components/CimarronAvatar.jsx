import React, { useState, useEffect, useRef } from 'react';
import { playPop } from '../utils/sfx';

const CimarronAvatar = ({ isSpeaking, mouthFrame, onAvatarClick, sfxEnabled, isThinking, isListening }) => {
  const [rotate, setRotate] = useState({ x: 0, y: 0 });
  const [isJumping, setIsJumping] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      
      const mouseX = e.clientX - centerX;
      const mouseY = e.clientY - centerY;

      const rotY = Math.max(-15, Math.min(15, (mouseX / (rect.width / 2)) * 15));
      const rotX = Math.max(-15, Math.min(15, -(mouseY / (rect.height / 2)) * 15));

      setRotate({ x: rotX, y: rotY });
    };

    const handleMouseLeave = () => {
      setRotate({ x: 0, y: 0 });
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, []);

  const handleClick = () => {
    setIsJumping(true);
    if (sfxEnabled) playPop();
    if (onAvatarClick) onAvatarClick();
    setTimeout(() => setIsJumping(false), 600);
  };

  let imageSrc = '/cimarron_boca_cerrada.webp';
  if (isListening) {
    imageSrc = '/Cimarron_Pensandoo.webp';
  } else if (isThinking) {
    imageSrc = '/cimarron_pensando.webp';
  } else if (isSpeaking) {
    // Alternar con las imágenes originales al hablar
    imageSrc = (mouthFrame % 2 === 0)
      ? '/cimarron_boca_cerrada.webp'
      : '/cimarron_boca_abierta.webp';
  }

  return (
    <div className="avatar-perspective-wrapper" ref={containerRef}>
      <div
        className={`avatar-container ${isJumping ? 'jumping' : 'floating'} ${isSpeaking ? 'speaking-active' : ''}`}
        style={{
          transform: `perspective(1000px) rotateX(${rotate.x}deg) rotateY(${rotate.y}deg)`,
        }}
        onClick={handleClick}
        title="¡Haz clic en el Cimarrón para saludarlo!"
      >
        {/* Anillos de Visualizador 360 (Ondas de Audio) */}
        {isSpeaking && (
          <div className="audio-visualizer-rings">
            <div className="ring ring-1"></div>
            <div className="ring ring-2"></div>
            <div className="ring ring-3"></div>
          </div>
        )}

        {/* Glow de energía UABC */}
        <div className="avatar-energy-glow" />

        <img
          src={imageSrc}
          alt="Cimarrón UABC"
          className="avatar-image"
          fetchpriority="high"
          loading="eager"
          width="400"
          height="450"
        />

        <div className="avatar-shadow" />
      </div>
    </div>
  );
};

export default CimarronAvatar;
