import React, { useState } from 'react';
import { X, MessageCircle, Phone, Send } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import apiClient from '@/lib/apiClient';

const WHATSAPP_NUMBER = '79999999999';
const PHONE_NUMBER = '+79999999999';

/**
 * Slim You — B3: "Talk to a Specialist" modal.
 * Three channels: WhatsApp, Call, Leave a request (form -> /api/specialist/request).
 */
export default function SpecialistContactModal({ open, onClose }) {
  const { t } = useLanguage();
  const [mode, setMode] = useState('options');
  const [name, setName] = useState('');
  const [contact, setContact] = useState('');
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  if (!open) return null;

  const close = () => {
    setMode('options');
    setName('');
    setContact('');
    setNote('');
    setDone(false);
    setSubmitting(false);
    onClose();
  };

  const handleWhatsapp = () => {
    window.open(`https://wa.me/${WHATSAPP_NUMBER}`, '_blank', 'noopener,noreferrer');
  };

  const handleCall = () => {
    window.location.href = `tel:${PHONE_NUMBER}`;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!contact.trim() || submitting) return;
    setSubmitting(true);
    try {
      await apiClient.post('/specialist/request', {
        name: name.trim() || null,
        contact: contact.trim(),
        note: note.trim() || null,
        channel: 'form',
      });
      setDone(true);
    } catch {
      setSubmitting(false);
    }
  };

  return (
    <div className="xc-specialist-overlay" onClick={close} data-testid="specialist-modal">
      <div className="xc-specialist-modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" onClick={close} className="xc-specialist-close" data-testid="specialist-close-btn">
          <X size={20} strokeWidth={1.5} />
        </button>

        <h3 className="xc-specialist-title">{t('talkToSpecialist')}</h3>

        {mode === 'options' && !done && (
          <div className="xc-specialist-options">
            <button
              type="button"
              data-testid="specialist-whatsapp-btn"
              className="xc-specialist-option"
              onClick={handleWhatsapp}
            >
              <MessageCircle size={20} strokeWidth={1.5} />
              <span>{t('whatsapp')}</span>
            </button>
            <button
              type="button"
              data-testid="specialist-call-btn"
              className="xc-specialist-option"
              onClick={handleCall}
            >
              <Phone size={20} strokeWidth={1.5} />
              <span>{t('callUs')}</span>
            </button>
            <button
              type="button"
              data-testid="specialist-form-btn"
              className="xc-specialist-option"
              onClick={() => setMode('form')}
            >
              <Send size={20} strokeWidth={1.5} />
              <span>{t('leaveRequest')}</span>
            </button>
          </div>
        )}

        {mode === 'form' && !done && (
          <form onSubmit={handleSubmit} className="xc-specialist-form" data-testid="specialist-form">
            <input
              data-testid="specialist-name-input"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t('yourName')}
              className="xc-specialist-input"
            />
            <input
              data-testid="specialist-contact-input"
              type="text"
              value={contact}
              onChange={(e) => setContact(e.target.value)}
              placeholder={t('yourContact')}
              required
              className="xc-specialist-input"
            />
            <textarea
              data-testid="specialist-note-input"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder={t('yourMessage')}
              rows={3}
              className="xc-specialist-input xc-specialist-textarea"
            />
            <button
              type="submit"
              data-testid="specialist-submit-btn"
              disabled={!contact.trim() || submitting}
              className="xc-specialist-submit"
            >
              {t('submit')}
            </button>
          </form>
        )}

        {done && (
          <div className="xc-specialist-done" data-testid="specialist-done">
            {t('requestSent')}
          </div>
        )}
      </div>
    </div>
  );
}
