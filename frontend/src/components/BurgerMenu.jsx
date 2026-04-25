import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import {
  X, User, Globe, Phone, Info, DollarSign, Smartphone,
  LogOut, ChevronRight,
} from 'lucide-react';
import { toast } from 'sonner';

export default function BurgerMenu({ open, onClose, onTalkToSpecialist }) {
  const { user, logout, isGuest } = useAuth();
  const { t, lang, setLang, languages } = useLanguage();
  const navigate = useNavigate();
  const [showLangs, setShowLangs] = React.useState(false);
  const [installEvent, setInstallEvent] = React.useState(null);

  // Capture beforeinstallprompt for "Get App"
  useEffect(() => {
    const handler = (e) => {
      e.preventDefault();
      setInstallEvent(e);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  if (!open) return null;

  const goTo = (path) => {
    onClose();
    navigate(path);
  };

  const handleLogout = async () => {
    onClose();
    await logout();
    navigate('/');
  };

  const handleTalkToSpecialist = () => {
    onClose();
    onTalkToSpecialist?.();
  };

  const handleGetApp = async () => {
    if (installEvent) {
      installEvent.prompt();
      await installEvent.userChoice;
      setInstallEvent(null);
      onClose();
    } else {
      toast(t('comingSoon'));
    }
  };

  return (
    <div className="menu-overlay" data-testid="burger-menu" onClick={onClose}>
      <div className="menu-panel" onClick={e => e.stopPropagation()}>
        <button data-testid="menu-close-btn" onClick={onClose} className="menu-close">
          <X size={24} />
        </button>

        <div className="menu-user-section">
          <div className="menu-user-avatar"><User size={24} /></div>
          <div>
            <p className="menu-user-name">{isGuest ? 'Guest' : (user?.name || user?.email?.split('@')[0])}</p>
            <p className="menu-user-email">{isGuest ? t('continueAsGuest') : user?.email}</p>
          </div>
        </div>

        <nav className="menu-nav">
          <button data-testid="menu-language-toggle" onClick={() => setShowLangs(!showLangs)} className="menu-item">
            <Globe size={20} /> <span>{t('language')}</span> <ChevronRight size={16} className={showLangs ? 'rotate-90' : ''} />
          </button>
          {showLangs && (
            <div className="menu-sub-grid" data-testid="language-grid">
              {languages.map(l => (
                <button
                  key={l.code}
                  data-testid={`lang-${l.code}`}
                  onClick={() => { setLang(l.code); setShowLangs(false); }}
                  className={`menu-lang-btn ${lang === l.code ? 'menu-lang-active' : ''}`}
                >
                  <span className="menu-lang-flag">{l.flag}</span>
                  <span>{l.native}</span>
                </button>
              ))}
            </div>
          )}

          <button data-testid="menu-account" onClick={() => goTo(isGuest ? '/auth' : '/profile')} className="menu-item">
            <User size={20} /> <span>{t('myAccount')}</span> <ChevronRight size={16} />
          </button>

          <button data-testid="menu-talk-specialist" onClick={handleTalkToSpecialist} className="menu-item">
            <Phone size={20} /> <span>{t('talkToSpecialist')}</span> <ChevronRight size={16} />
          </button>

          <button data-testid="menu-about-clinic" onClick={() => goTo('/about')} className="menu-item">
            <Info size={20} /> <span>{t('aboutClinic')}</span> <ChevronRight size={16} />
          </button>

          <button data-testid="menu-pricing" onClick={() => goTo('/tariffs')} className="menu-item">
            <DollarSign size={20} /> <span>{t('pricing')}</span> <ChevronRight size={16} />
          </button>

          <button data-testid="menu-get-app" onClick={handleGetApp} className="menu-item menu-item-highlight">
            <Smartphone size={20} /> <span>{t('getApp')}</span> <ChevronRight size={16} />
          </button>
        </nav>

        {!isGuest && (
          <button data-testid="menu-logout" onClick={handleLogout} className="menu-logout">
            <LogOut size={20} /> <span>{t('logout')}</span>
          </button>
        )}
      </div>
    </div>
  );
}
