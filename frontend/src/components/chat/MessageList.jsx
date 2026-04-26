import React from 'react';
import { Volume2, VolumeX } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '@/contexts/LanguageContext';
import IntakeCard from '@/components/chat/IntakeCard';

export default function MessageList({ messages, loading, playingTTS, playTTS, stopTTS, messagesEndRef, activeVoice, onIntakeAnswer }) {
  const navigate = useNavigate();
  const { t } = useLanguage();

  const typingLabel = activeVoice === 'female' ? t('typingKylie') : t('typingLeon');
  const typingAvatar = activeVoice === 'female' ? '/kylie-avatar.jpg' : '/leon-avatar.jpg';

  return (
    <>
      {messages.map((msg, i) => (
        <React.Fragment key={msg.id || `msg-${i}`}>
          <div
            className={`xc-chat-message ${msg.role === 'user' ? 'user' : 'assistant'}${msg.image ? ' has-image' : ''}`}
            data-testid={`chat-message-${i}`}
          >
            {msg.image && (
              <>
                <img src={msg.image} alt="Sent" className="xc-chat-message-image" />
                <p className="xc-chat-message-image-caption" data-testid={`photo-sent-caption-${i}`}>{t('photoSent')}</p>
              </>
            )}
            {msg.content && msg.content.split('\n').map((line, j) => (
              <p key={`${msg.id}-line-${j}`}>{line}</p>
            ))}
            {msg.intakeQuestion && !msg.intakeAnswered && (
              <IntakeCard question={msg.intakeQuestion} onAnswer={onIntakeAnswer} />
            )}
            {msg.role === 'ai' && !msg.isTariffPrompt && !msg.intakeQuestion && (
              <button
                data-testid={`tts-play-${i}`}
                onClick={() => playingTTS === i ? stopTTS() : playTTS(msg.content, i, activeVoice)}
                className={`xc-msg-speaker-btn ${playingTTS === i ? 'playing' : ''}`}
              >
                {playingTTS === i ? <VolumeX size={14} strokeWidth={1.5} /> : <Volume2 size={14} strokeWidth={1.5} />}
              </button>
            )}
          </div>
          {msg.isTariffPrompt && (
            <button data-testid="go-to-tariffs-btn" onClick={() => navigate('/tariffs')} className="xc-tariff-btn">
              {t('tariffs')}
            </button>
          )}
        </React.Fragment>
      ))}
      {loading && (
        <div className="xc-typing-wrap" data-testid="chat-loading">
          <img src={typingAvatar} alt="" className="xc-typing-avatar" />
          <div className="xc-chat-message assistant typing">
            <span className="dot" /><span className="dot" /><span className="dot" />
          </div>
          <span className="xc-typing-label" data-testid="typing-label">{typingLabel}…</span>
        </div>
      )}
      <div ref={messagesEndRef} />
    </>
  );
}
