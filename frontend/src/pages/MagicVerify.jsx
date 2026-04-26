import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import apiClient from '@/lib/apiClient';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';

/**
 * /magic/:token — single-use entry point from email/WhatsApp magic links.
 * Calls /auth/magic/verify, lets the cookie auth take over, then sends the
 * user straight into the chat.
 */
export default function MagicVerify() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const { t } = useLanguage();
  const [error, setError] = useState(null);
  const calledRef = useRef(false);

  useEffect(() => {
    if (calledRef.current) return;
    calledRef.current = true;
    (async () => {
      try {
        await apiClient.post('/auth/magic/verify', { token });
        await refreshUser();
        navigate('/chat', { replace: true });
      } catch (err) {
        setError(err?.response?.data?.detail || t('errorTryAgain') || 'Link is invalid or expired.');
      }
    })();
  }, [token, navigate, refreshUser, t]);

  return (
    <div className="loading-screen" data-testid="magic-verify-page">
      {error ? (
        <div style={{ textAlign: 'center', padding: '2rem', maxWidth: 360 }}>
          <p data-testid="magic-verify-error" style={{ marginBottom: '1rem' }}>{error}</p>
          <button
            type="button"
            onClick={() => navigate('/', { replace: true })}
            data-testid="magic-verify-home-btn"
            style={{
              background: 'rgba(255,255,255,0.1)', color: '#fff', border: 'none',
              padding: '0.6rem 1.6rem', borderRadius: 999, cursor: 'pointer',
            }}
          >
            {t('back') || 'Back'}
          </button>
        </div>
      ) : (
        <div className="loading-spinner" />
      )}
    </div>
  );
}
