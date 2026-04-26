import React from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Heart, Mail, Shield } from 'lucide-react';

export default function AboutPage() {
  const { t } = useLanguage();
  const navigate = useNavigate();

  return (
    <div className="about-page" data-testid="about-page">
      <header className="page-header">
        <button data-testid="about-back-btn" onClick={() => navigate(-1)} className="header-back-btn">
          <ArrowLeft size={20} />
        </button>
        <h1>{t('about')}</h1>
      </header>

      <div className="about-content">
        <div className="about-hero">
          <Heart size={48} className="about-icon" />
          <h2 className="about-title">{t('missionTitle')}</h2>
          <p className="about-text">{t('missionText')}</p>
        </div>

        <div className="about-section" data-testid="contacts-section">
          <h3>{t('contacts')}</h3>
          <div className="about-links-grid">
            <a href="mailto:support@slimlight.app" className="about-link-card" data-testid="link-email">
              <Mail size={20} />
              <span>support@slimlight.app</span>
            </a>
          </div>
        </div>

        <div className="about-disclaimer">
          <Shield size={16} />
          <p>SlimLight does not provide medical diagnoses. In case of crisis, please contact your local emergency line.</p>
        </div>
      </div>
    </div>
  );
}
