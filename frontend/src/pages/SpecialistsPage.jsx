import React from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Award, GraduationCap, Users, Heart, ExternalLink } from 'lucide-react';

const MIRON_PHOTO = 'https://customer-assets.emergentagent.com/job_xicon-preview-3/artifacts/da8jruwh_bbSt44ErT9oMjoxUeM0T1pEHQxCQwYb0Q9QsI9mn.webp';
const MIRON_PHOTO_2 = 'https://customer-assets.emergentagent.com/job_xicon-preview-3/artifacts/p4a7djrm_a2ceHzRs7mSOhk3UJsLG4RwEWT4PfMmLizx1oiZo.webp';

export default function SpecialistsPage() {
  const { t } = useLanguage();
  const navigate = useNavigate();

  return (
    <div className="specialists-page" data-testid="specialists-page">
      <header className="page-header">
        <button data-testid="specialists-back-btn" onClick={() => navigate(-1)} className="header-back-btn">
          <ArrowLeft size={20} />
        </button>
        <h1>{t('specialists')}</h1>
      </header>

      <div className="expert-card-featured" data-testid="expert-card-leon">
        <div className="expert-photos">
          <img src={MIRON_PHOTO} alt="Leon Shakira" className="expert-photo-main" />
          <img src={MIRON_PHOTO_2} alt="Leon Shakira" className="expert-photo-secondary" />
        </div>
        <div className="expert-info">
          <h2 className="expert-name">Leon Shakira</h2>
          <p className="expert-title">
            <Award size={16} />
            Dietologist, Nutritionist | Psychologist
          </p>
          <p className="expert-subtitle">
            <GraduationCap size={16} />
            ISSA (USA) — Master Trainer
          </p>
          <div className="expert-credentials">
            <span className="expert-cred-tag">Stanford University</span>
            <span className="expert-cred-tag">Emory University</span>
            <span className="expert-cred-tag">Edinburgh University</span>
            <span className="expert-cred-tag">LMU Munich</span>
            <span className="expert-cred-tag">UNC</span>
          </div>
          <div className="expert-stats">
            <div className="expert-stat">
              <Users size={16} />
              <span>10 000+ clients since 2012</span>
            </div>
            <div className="expert-stat">
              <Heart size={16} />
              <span>Father of 7, family man</span>
            </div>
          </div>
          <p className="expert-description">
            Specializes in psychology of weight loss and eating behavior. Consults families of political elites, businessmen, and entertainment industry.
          </p>
          <a
            href="https://shakiraleon.taplink.ws"
            target="_blank"
            rel="noopener noreferrer"
            className="expert-link"
            data-testid="expert-book-btn"
          >
            <ExternalLink size={16} />
            {t('bookConsultation')}
          </a>
        </div>
      </div>
    </div>
  );
}
