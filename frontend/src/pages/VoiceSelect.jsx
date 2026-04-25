import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import apiClient from '@/lib/apiClient';
import { User } from 'lucide-react';

export default function VoiceSelect() {
  const { t } = useLanguage();
  const { refreshUser } = useAuth();
  const navigate = useNavigate();
  const [selected, setSelected] = useState(null);

  const handleSelect = async (voice) => {
    setSelected(voice);
    try {
      await apiClient.put('/user/voice', { voice });
      await refreshUser();
      navigate('/chat');
    } catch (err) {
      if (process.env.NODE_ENV === 'development') console.error('Voice update failed:', err.message);
    }
  };

  return (
    <div className="voice-page" data-testid="voice-select-page">
      <h1 className="voice-title">{t('chooseVoice')}</h1>
      <div className="voice-options">
        <button
          data-testid="voice-male-btn"
          onClick={() => handleSelect('male')}
          className={`voice-card ${selected === 'male' ? 'voice-card-selected' : ''}`}
        >
          <div className="voice-avatar voice-avatar-male">
            <User size={48} />
          </div>
          <span className="voice-label">Leon</span>
          <span className="voice-sublabel">{t('male')}</span>
        </button>

        <button
          data-testid="voice-female-btn"
          onClick={() => handleSelect('female')}
          className={`voice-card ${selected === 'female' ? 'voice-card-selected' : ''}`}
        >
          <div className="voice-avatar voice-avatar-female">
            <User size={48} />
          </div>
          <span className="voice-label">Kylie</span>
          <span className="voice-sublabel">{t('female')}</span>
        </button>
      </div>
    </div>
  );
}
