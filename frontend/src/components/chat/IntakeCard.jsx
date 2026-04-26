import React, { useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { getIntakeButtons } from '@/config/intakeQuestions';

/**
 * Intake question card rendered inline inside the chat message list.
 * Localized for all 8 supported UI languages.
 */
export default function IntakeCard({ question, onAnswer }) {
  const { lang } = useLanguage();
  const labels = getIntakeButtons(lang);

  const [selected, setSelected] = useState(question.type.startsWith('multi') ? [] : '');
  const [custom, setCustom] = useState('');
  const [fields, setFields] = useState({});

  const isMulti = question.type.startsWith('multi');
  const isData = question.type === 'data';
  const hasCustom = question.type.endsWith('_custom') || isMulti;

  const toggle = (opt) => {
    if (isMulti) {
      setSelected((prev) => prev.includes(opt) ? prev.filter((x) => x !== opt) : [...prev, opt]);
    } else {
      setSelected(opt);
      // Single without custom — submit immediately.
      if (!hasCustom) onAnswer(question.id, opt);
    }
  };

  const submit = () => {
    if (isMulti) {
      const all = [...selected, ...(custom.trim() ? [custom.trim()] : [])];
      if (all.length) onAnswer(question.id, all.join(', '));
      return;
    }
    const ans = custom.trim() || selected;
    if (ans) onAnswer(question.id, ans);
  };

  const submitData = () => {
    const age = (fields.age || '').trim();
    const weight = (fields.weight || '').trim();
    const height = (fields.height || '').trim();
    if (!age || !weight || !height) return;
    onAnswer(question.id, `${labels.field_age}: ${age}, ${labels.field_weight}: ${weight}, ${labels.field_height}: ${height}`, {
      q4_age: age, q4_weight: weight, q4_height: height,
    });
  };

  return (
    <div className="xc-intake-card" data-testid={`intake-${question.id}`}>
      <div className="xc-intake-question">{question.text}</div>
      {isData ? (
        <div className="xc-intake-fields">
          {question.fields.map((f) => (
            <input
              key={f.key}
              className="xc-intake-input"
              type="number"
              inputMode="numeric"
              placeholder={labels[`field_${f.key}`] || f.label}
              value={fields[f.key] || ''}
              onChange={(e) => setFields((p) => ({ ...p, [f.key]: e.target.value }))}
              data-testid={`intake-${question.id}-${f.key}`}
            />
          ))}
          <button className="xc-intake-submit" onClick={submitData} data-testid={`intake-${question.id}-submit`}>
            {labels.next}
          </button>
        </div>
      ) : (
        <div className="xc-intake-options">
          {question.options.map((opt) => {
            const active = isMulti ? selected.includes(opt) : selected === opt;
            return (
              <button
                key={opt}
                className={`xc-intake-btn ${active ? 'xc-intake-btn-active' : ''}`}
                onClick={() => toggle(opt)}
                data-testid={`intake-${question.id}-opt-${opt.slice(0, 10)}`}
              >
                {opt}
              </button>
            );
          })}
          {hasCustom && (
            <input
              className="xc-intake-custom"
              placeholder={labels.custom}
              value={custom}
              onChange={(e) => setCustom(e.target.value)}
              data-testid={`intake-${question.id}-custom`}
            />
          )}
          {hasCustom && (
            <button className="xc-intake-submit" onClick={submit} data-testid={`intake-${question.id}-submit`}>
              {labels.done}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
