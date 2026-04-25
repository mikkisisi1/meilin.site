import React from 'react';
import { useNavigate } from 'react-router-dom';

export default function LandingPage() {
  const navigate = useNavigate();
  const goToChat = () => navigate('/chat');

  return (
    <div
      className="landing-video-root"
      data-testid="landing-page"
      style={{
        position: 'fixed',
        inset: 0,
        width: '100vw',
        height: '100vh',
        background: '#000',
        overflow: 'hidden',
        margin: 0,
        padding: 0,
      }}
    >
      <video
        data-testid="landing-video"
        src="/media/landing.mp4"
        poster="/media/landing-poster.jpg"
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        disablePictureInPicture
        controlsList="nodownload nofullscreen noremoteplayback"
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          background: '#000',
        }}
        onClick={goToChat}
      />
      <button
        type="button"
        data-testid="landing-cta-overlay"
        aria-label="Перейти в чат"
        onClick={goToChat}
        style={{
          position: 'absolute',
          left: '50%',
          bottom: '8%',
          transform: 'translateX(-50%)',
          width: 'min(72vw, 360px)',
          height: 'clamp(56px, 9vh, 88px)',
          background: 'transparent',
          border: 'none',
          outline: 'none',
          padding: 0,
          margin: 0,
          cursor: 'pointer',
          WebkitTapHighlightColor: 'transparent',
          zIndex: 2,
        }}
      />
    </div>
  );
}
