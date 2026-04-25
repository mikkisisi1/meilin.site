import React from 'react';
import { useLanguage } from '@/contexts/LanguageContext';

/**
 * Slim You — B1: Quick reply chips.
 * Shown above the input area when:
 *   - voice is chosen,
 *   - intake is not in progress (intakeStep === -1 or -2 / done),
 *   - user has nothing typed and we are not loading.
 */
export default function QuickReplies({ onPick, disabled }) {
  const { t } = useLanguage();

  const replies = [
    { key: 'good', label: t('quickReplyGood') },
    { key: 'support', label: t('quickReplyNeedSupport') },
    { key: 'food', label: t('quickReplyAskFood') },
  ];

  return (
    <div className="xc-quick-replies" data-testid="quick-replies">
      {replies.map((r) => (
        <button
          key={r.key}
          type="button"
          data-testid={`quick-reply-${r.key}`}
          className="xc-quick-reply-chip"
          onClick={() => onPick(r.label)}
          disabled={disabled}
        >
          {r.label}
        </button>
      ))}
    </div>
  );
}
