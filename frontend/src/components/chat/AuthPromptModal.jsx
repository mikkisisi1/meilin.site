import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Mail, MessageCircle, ArrowLeft } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { toast } from 'sonner';
import apiClient from '@/lib/apiClient';

/**
 * Slim You — post-questionnaire auth prompt (guests only).
 * Three real channels:
 *   - Google → existing /auth screen.
 *   - Email magic-link → POST /auth/magic/request {channel: 'email'}.
 *   - WhatsApp magic-link → POST /auth/magic/request {channel: 'whatsapp'}.
 * Apple is left as "Coming soon" — no Apple ID integration yet.
 */
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^\+[1-9]\d{6,14}$/;

export default function AuthPromptModal({ open, onClose }) {
  const { t } = useLanguage();
  const navigate = useNavigate();
  const [mode, setMode] = useState('choose'); // choose | email | whatsapp | sent
  const [destination, setDestination] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!open) return null;

  const handleEmail = () => navigate('/auth') || onClose();
  const handleSoon = () => toast(t('comingSoon'));

  const reset = () => {
    setMode('choose');
    setDestination('');
    setSubmitting(false);
  };
  const handleClose = () => { reset(); onClose(); };

  const submitMagicLink = async (channel) => {
    const dest = destination.trim();
    if (channel === 'email' && !EMAIL_RE.test(dest)) {
      toast(t('invalidEmail') || 'Please enter a valid email');
      return;
    }
    if (channel === 'whatsapp' && !PHONE_RE.test(dest)) {
      toast(t('invalidPhone') || 'Use international format, e.g. +14155550123');
      return;
    }
    setSubmitting(true);
    try {
      await apiClient.post('/auth/magic/request', { channel, destination: dest });
      setMode('sent');
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast(typeof detail === 'string' ? detail : (t('errorTryAgain') || 'Could not send link'));
      setSubmitting(false);
    }
  };

  return (
    <div className="xc-auth-prompt-overlay" onClick={handleClose} data-testid="auth-prompt-modal">
      <div className="xc-auth-prompt-modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" onClick={handleClose} className="xc-auth-prompt-close" data-testid="auth-prompt-close-btn">
          <X size={20} strokeWidth={1.5} />
        </button>

        {mode === 'choose' && (
          <>
            <h3 className="xc-auth-prompt-title">{t('saveProgress')}</h3>
            <p className="xc-auth-prompt-desc">{t('saveProgressDesc')}</p>
            <div className="xc-auth-prompt-options">
              <button
                type="button"
                data-testid="auth-google-btn"
                className="xc-auth-prompt-option xc-auth-prompt-google"
                onClick={handleEmail}
              >
                <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
                  <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3c-1.7 4.7-6.2 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z"/>
                  <path fill="#FF3D00" d="M6.3 14.1l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34 6.1 29.3 4 24 4c-7.7 0-14.4 4.4-17.7 10.1z"/>
                  <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35 26.7 36 24 36c-5.1 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z"/>
                  <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.3 4.3-4.2 5.6l6.2 5.2C40.8 36 44 30.5 44 24c0-1.3-.1-2.4-.4-3.5z"/>
                </svg>
                <span>{t('continueWithGoogle')}</span>
              </button>

              <button
                type="button"
                data-testid="auth-email-btn"
                className="xc-auth-prompt-option xc-auth-prompt-google"
                onClick={() => setMode('email')}
              >
                <Mail size={18} strokeWidth={1.5} />
                <span>{t('emailMagicLink') || 'Email me a link'}</span>
              </button>

              <button
                type="button"
                data-testid="auth-whatsapp-btn"
                className="xc-auth-prompt-option xc-auth-prompt-whatsapp"
                onClick={() => setMode('whatsapp')}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="#25D366" aria-hidden="true">
                  <path d="M20.52 3.48A11.92 11.92 0 0 0 12.05 0C5.5 0 .17 5.33.17 11.88c0 2.09.55 4.13 1.6 5.93L0 24l6.34-1.66a11.86 11.86 0 0 0 5.7 1.45h.01c6.55 0 11.88-5.33 11.88-11.88a11.8 11.8 0 0 0-3.41-8.43zm-8.47 18.27h-.01a9.86 9.86 0 0 1-5.03-1.38l-.36-.21-3.76.98 1-3.66-.23-.38a9.84 9.84 0 0 1-1.51-5.22c0-5.45 4.43-9.88 9.9-9.88 2.65 0 5.13 1.03 7 2.9a9.83 9.83 0 0 1 2.9 6.99c0 5.45-4.43 9.86-9.9 9.86z"/>
                </svg>
                <span>{t('continueWithWhatsapp')}</span>
              </button>

              <button
                type="button"
                data-testid="auth-apple-btn"
                className="xc-auth-prompt-option xc-auth-prompt-apple"
                onClick={handleSoon}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M16.365 1.43c0 1.14-.493 2.27-1.177 3.08-.744.9-1.99 1.57-2.987 1.57-.12 0-.23-.02-.3-.03-.01-.06-.04-.22-.04-.39 0-1.15.572-2.27 1.206-2.98.804-.94 2.142-1.64 3.248-1.68.03.13.05.28.05.43zm4.565 17.04c-.45.96-.66 1.39-1.245 2.24-.815 1.16-1.96 2.6-3.39 2.62-1.27.02-1.6-.83-3.32-.83-1.72 0-2.08.81-3.34.84-1.4.03-2.46-1.27-3.28-2.43-2.31-3.28-2.55-7.13-1.13-9.18 1.01-1.46 2.61-2.31 4.11-2.31 1.53 0 2.49.84 3.75.84 1.22 0 1.97-.84 3.74-.84 1.34 0 2.76.73 3.78 2-3.32 1.81-2.78 6.55.32 7.05z"/>
                </svg>
                <span>{t('continueWithApple')}</span>
              </button>

              <button
                type="button"
                data-testid="auth-guest-btn"
                className="xc-auth-prompt-guest"
                onClick={handleClose}
              >
                {t('continueAsGuest')}
              </button>
            </div>
          </>
        )}

        {(mode === 'email' || mode === 'whatsapp') && (
          <>
            <button
              type="button"
              onClick={() => { setMode('choose'); setDestination(''); }}
              data-testid="auth-back-btn"
              className="xc-auth-prompt-close"
              style={{ left: 16, right: 'auto' }}
              aria-label="Back"
            >
              <ArrowLeft size={20} strokeWidth={1.5} />
            </button>
            <h3 className="xc-auth-prompt-title">
              {mode === 'email' ? (t('emailMagicLink') || 'Email me a link') : t('continueWithWhatsapp')}
            </h3>
            <p className="xc-auth-prompt-desc">
              {mode === 'email'
                ? (t('emailMagicLinkDesc') || "We'll send a one-tap link to your inbox.")
                : (t('whatsappMagicLinkDesc') || "We'll send a one-tap link to your WhatsApp.")}
            </p>
            <input
              type={mode === 'email' ? 'email' : 'tel'}
              data-testid={mode === 'email' ? 'magic-email-input' : 'magic-phone-input'}
              autoFocus
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              placeholder={mode === 'email' ? 'you@example.com' : '+14155550123'}
              disabled={submitting}
              style={{
                width: '100%', padding: '0.75rem 1rem', borderRadius: 12,
                border: '1px solid rgba(255,255,255,0.2)', background: 'rgba(255,255,255,0.06)',
                color: '#fff', fontSize: 16, marginBottom: '0.75rem',
              }}
              onKeyDown={(e) => { if (e.key === 'Enter') submitMagicLink(mode); }}
            />
            <button
              type="button"
              data-testid={mode === 'email' ? 'magic-email-submit' : 'magic-phone-submit'}
              className="xc-auth-prompt-option xc-auth-prompt-google"
              disabled={submitting || !destination.trim()}
              onClick={() => submitMagicLink(mode)}
              style={{ justifyContent: 'center' }}
            >
              {mode === 'email' ? <Mail size={18} strokeWidth={1.5} /> : <MessageCircle size={18} strokeWidth={1.5} />}
              <span>{submitting ? (t('sending') || 'Sending…') : (t('sendLink') || 'Send link')}</span>
            </button>
          </>
        )}

        {mode === 'sent' && (
          <>
            <h3 className="xc-auth-prompt-title">{t('linkSent') || 'Link sent ✨'}</h3>
            <p className="xc-auth-prompt-desc" data-testid="magic-sent-msg">
              {t('linkSentDesc') || 'Check your inbox or WhatsApp — tap the link to continue your session anywhere.'}
            </p>
            <button
              type="button"
              data-testid="magic-sent-close"
              className="xc-auth-prompt-guest"
              onClick={handleClose}
            >
              {t('continueAsGuest') || 'Continue'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
