import React from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Heart, ExternalLink, Mail, Shield } from 'lucide-react';

const MIRON_PHOTO = 'https://customer-assets.emergentagent.com/job_xicon-preview-3/artifacts/p4a7djrm_a2ceHzRs7mSOhk3UJsLG4RwEWT4PfMmLizx1oiZo.webp';

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

        <div className="about-expert">
          <img src={MIRON_PHOTO} alt="Leon Shakira" className="about-expert-photo" />
          <div>
            <h3>{t('expert')}: Leon Shakira</h3>
            <p>Psychologist, Dietologist, Nutritionist (ISSA USA)</p>
          </div>
        </div>

        <div className="about-section" data-testid="contacts-section">
          <h3>{t('contacts')}</h3>
          <div className="about-links-grid">
            <a href="mailto:support@miro.care" className="about-link-card">
              <Mail size={20} />
              <span>support@miro.care</span>
            </a>
            <a href="https://shakiraleon.taplink.ws" target="_blank" rel="noopener noreferrer" className="about-link-card">
              <ExternalLink size={20} />
              <span>TapLink</span>
            </a>
          </div>
        </div>

        <div className="about-section">
          <h3>{t('links')}</h3>
          <div className="about-links-grid">
            <a href="https://t.me/mirocare" target="_blank" rel="noopener noreferrer" className="about-link-card" data-testid="link-telegram">
              <span>Telegram</span>
            </a>
            <a href="https://wa.me/mirocare" target="_blank" rel="noopener noreferrer" className="about-link-card" data-testid="link-whatsapp">
              <span>WhatsApp</span>
            </a>
            <a href="https://instagram.com/mirocare" target="_blank" rel="noopener noreferrer" className="about-link-card" data-testid="link-instagram">
              <span>Instagram</span>
            </a>
          </div>
        </div>

        <div className="about-disclaimer">
          <Shield size={16} />
          <p>Miro.Care does not provide medical diagnoses. In case of crisis, please contact your local emergency line.</p>
        </div>
      </div>
    </div>
  );
}
