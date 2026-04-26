import React, { useEffect, useState, useCallback } from 'react';
import { Download, X, Check, Loader } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import '@/components/InstallPrompt.css';

const DISMISS_KEY = 'miro_install_dismissed_until';
const TRIGGER_EVENT = 'miro:show-install-prompt';
const DISMISS_DAYS = 7;

function isStandalone() {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(display-mode: standalone)').matches
    || window.navigator.standalone === true;
}

function isDismissed() {
  try {
    const until = Number(localStorage.getItem(DISMISS_KEY) || 0);
    return Date.now() < until;
  } catch { return false; }
}

function markDismissed() {
  try {
    localStorage.setItem(DISMISS_KEY, String(Date.now() + DISMISS_DAYS * 86400000));
  } catch { /* ignore */ }
}

export default function InstallPrompt() {
  const { t } = useLanguage();
  const [deferred, setDeferred] = useState(null);
  const [visible, setVisible] = useState(false);
  const [status, setStatus] = useState('idle'); // idle | installing | installed | error

  // Capture beforeinstallprompt
  useEffect(() => {
    if (isStandalone() || isDismissed()) return;

    const onPrompt = (e) => {
      e.preventDefault();
      setDeferred(e);
    };
    window.addEventListener('beforeinstallprompt', onPrompt);

    const onInstalled = () => {
      setStatus('installed');
      markDismissed();
      setTimeout(() => setVisible(false), 1800);
    };
    window.addEventListener('appinstalled', onInstalled);

    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, []);

  // Contextual reveal — wait for an explicit "earned" trigger (e.g. intake
  // completion). This is far less annoying than a timer-based popup on landing
  // and converts better because the user has already invested in the product.
  useEffect(() => {
    if (isStandalone() || isDismissed()) return;
    const onTrigger = () => setVisible(true);
    window.addEventListener(TRIGGER_EVENT, onTrigger);
    return () => window.removeEventListener(TRIGGER_EVENT, onTrigger);
  }, []);

  const handleInstall = useCallback(async () => {
    if (!deferred) {
      // Fallback: no native prompt (iOS Safari / already cached) — just mark as dismissed-for-now
      markDismissed();
      setVisible(false);
      return;
    }
    setStatus('installing');
    try {
      await deferred.prompt();
      const choice = await deferred.userChoice;
      if (choice.outcome === 'accepted') {
        setStatus('installed');
        markDismissed();
        setTimeout(() => setVisible(false), 1800);
      } else {
        setStatus('idle');
        markDismissed();
        setVisible(false);
      }
    } catch {
      setStatus('error');
    } finally {
      setDeferred(null);
    }
  }, [deferred]);

  const handleClose = useCallback(() => {
    markDismissed();
    setVisible(false);
  }, []);

  if (!visible) return null;

  return (
    <div className="miro-install-backdrop" data-testid="install-prompt">
      <div className="miro-install-card" role="dialog" aria-live="polite">
        <button
          className="miro-install-close"
          onClick={handleClose}
          data-testid="install-close-btn"
          aria-label={t('close') || 'Close'}
        >
          <X size={18} strokeWidth={2} />
        </button>

        <img
          src="/icon-192.png"
          alt="Miro.Care"
          className="miro-install-icon"
          data-testid="install-icon"
        />

        <div className="miro-install-text">
          <h3 className="miro-install-title" data-testid="install-title">
            {t('installTitle')}
          </h3>
          <p className="miro-install-sub" data-testid="install-subtitle">
            {t('installSubtitle')}
          </p>
        </div>

        <button
          className="miro-install-btn"
          onClick={handleInstall}
          disabled={status === 'installing' || status === 'installed'}
          data-testid="install-btn"
        >
          {status === 'idle' && (<><Download size={18} strokeWidth={2} /> {t('installCta')}</>)}
          {status === 'installing' && (<><Loader size={18} strokeWidth={2} className="miro-install-spin" /> {t('installing')}</>)}
          {status === 'installed' && (<><Check size={18} strokeWidth={2} /> {t('installed')}</>)}
          {status === 'error' && (<><Download size={18} strokeWidth={2} /> {t('installRetry')}</>)}
        </button>

        {/* Determinate-ish progress bar during install */}
        {status === 'installing' && (
          <div className="miro-install-bar" data-testid="install-progress">
            <div className="miro-install-bar-fill" />
          </div>
        )}
      </div>
    </div>
  );
}
