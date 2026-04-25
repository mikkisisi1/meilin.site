import React, { useEffect, useRef } from 'react';
import { Trash2 } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';

/**
 * Slim You — B4: ⋯ context menu inside chat header.
 * Currently exposes a single action: "Clear chat".
 */
export default function HeaderMenu({ open, onClose, onClearChat }) {
  const ref = useRef(null);
  const { t } = useLanguage();

  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    };
    document.addEventListener('mousedown', handler);
    document.addEventListener('touchstart', handler);
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('touchstart', handler);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="xc-header-menu-popup" ref={ref} data-testid="header-menu-popup">
      <button
        type="button"
        className="xc-header-menu-item"
        data-testid="clear-chat-btn"
        onClick={onClearChat}
      >
        <Trash2 size={16} strokeWidth={1.5} />
        <span>{t('clearChat')}</span>
      </button>
    </div>
  );
}
