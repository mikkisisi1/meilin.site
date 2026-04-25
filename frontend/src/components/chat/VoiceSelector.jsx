import React from 'react';

export default function VoiceSelector({ onSelect, t }) {
  return (
    <div className="xc-voice-select-prompt" data-testid="voice-select-prompt">
      <div className="xc-voice-select-avatars">
        <button className="xc-voice-avatar-card" onClick={() => onSelect('male')} data-testid="voice-pick-leon">
          <div className="xc-voice-avatar-circle">
            <img src="/leon-avatar.jpg" alt="Leon" />
          </div>
          <span className="xc-voice-avatar-label">Leon</span>
        </button>
        <button className="xc-voice-avatar-card" onClick={() => onSelect('female')} data-testid="voice-pick-kylie">
          <div className="xc-voice-avatar-circle">
            <img src="/kylie-avatar.jpg" alt="Kylie" />
          </div>
          <span className="xc-voice-avatar-label">Kylie</span>
        </button>
      </div>
      <p className="xc-voice-select-hint">{t('chooseVoice') || 'Choose your consultant'}</p>
    </div>
  );
}
