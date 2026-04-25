import React, { useState } from 'react';
import { ArrowLeft, Volume2, VolumeX, Menu, MoreVertical } from 'lucide-react';
import HeaderMenu from './HeaderMenu';

export default function ChatHeader({
  voiceChosen, activeVoice, onVoiceSelect,
  ttsEnabled, toggleTTS,
  isFreePhase, hasMinutes, minutesLeft, formatTime,
  onBack, freeSessionLabel, countdownSeconds,
  onMenuOpen, isBusy, onClearChat,
}) {
  const [moreOpen, setMoreOpen] = useState(false);
  const showCountdown = countdownSeconds !== null && countdownSeconds >= 0;

  return (
    <div className="xc-chat-header" data-testid="chat-header">
      <button data-testid="chat-back-btn" onClick={onBack} className="xc-close-btn">
        <ArrowLeft size={20} strokeWidth={1.5} />
      </button>

      <div className="xc-chat-agent-info">
        <div className="xc-chat-avatars-row">
          <button
            className={`xc-chat-avatar-item ${!voiceChosen ? 'xc-avatar-selectable' : ''} ${activeVoice === 'male' ? 'xc-avatar-active' : ''} ${voiceChosen && activeVoice !== 'male' ? 'xc-avatar-dim' : ''}`}
            onClick={() => onVoiceSelect('male')}
            data-testid="avatar-leon-btn"
          >
            <div className="xc-chat-avatar-wrapper">
              <img src="/leon-avatar.jpg" alt="Leon" className="xc-chat-avatar-img" />
              {activeVoice === 'male' && isBusy && <span className="xc-chat-thinking-dot" data-testid="thinking-dot-leon" />}
            </div>
            <span className="xc-avatar-name">Leon</span>
          </button>
          <span className="xc-avatar-separator" aria-hidden="true">•</span>
          <button
            className={`xc-chat-avatar-item ${!voiceChosen ? 'xc-avatar-selectable' : ''} ${activeVoice === 'female' ? 'xc-avatar-active' : ''} ${voiceChosen && activeVoice !== 'female' ? 'xc-avatar-dim' : ''}`}
            onClick={() => onVoiceSelect('female')}
            data-testid="avatar-kylie-btn"
          >
            <div className="xc-chat-avatar-wrapper">
              <img src="/kylie-avatar.jpg" alt="Kylie" className="xc-chat-avatar-img" />
              {activeVoice === 'female' && isBusy && <span className="xc-chat-thinking-dot" data-testid="thinking-dot-kylie" />}
            </div>
            <span className="xc-avatar-name">Kylie</span>
          </button>
        </div>
      </div>

      <div className="xc-header-right">
        {showCountdown && (
          <span className="xc-countdown" data-testid="countdown-timer">
            {countdownSeconds}
          </span>
        )}
        <button
          data-testid="tts-toggle-btn"
          onClick={toggleTTS}
          className={`xc-header-icon-btn ${ttsEnabled ? 'active' : ''}`}
        >
          {ttsEnabled ? <Volume2 size={18} strokeWidth={1.5} /> : <VolumeX size={18} strokeWidth={1.5} />}
        </button>

        <div className="xc-header-more-wrap">
          <button
            data-testid="header-more-btn"
            onClick={() => setMoreOpen((v) => !v)}
            className="xc-header-icon-btn"
            aria-label="More"
          >
            <MoreVertical size={18} strokeWidth={1.5} />
          </button>
          <HeaderMenu
            open={moreOpen}
            onClose={() => setMoreOpen(false)}
            onClearChat={() => {
              setMoreOpen(false);
              onClearChat?.();
            }}
          />
        </div>

        <button
          data-testid="chat-menu-btn"
          onClick={onMenuOpen}
          className="xc-header-icon-btn"
        >
          <Menu size={18} strokeWidth={1.5} />
        </button>
      </div>
    </div>
  );
}
