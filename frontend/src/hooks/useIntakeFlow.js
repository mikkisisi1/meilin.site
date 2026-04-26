import { useState, useCallback } from 'react';
import {
  getIntakeQuestions,
  getIntakeIntro,
  getIntakeOutro,
  nextIntakeStep,
  buildIntakeSummary,
} from '@/config/intakeQuestions';

/**
 * Encapsulates the intake (questionnaire) flow that runs before the user
 * enters free-form chat. Exposes:
 *   - intakeStep      — -1 (not started) | 0..N (Qi index) | -2 (done)
 *   - intakeAnswers   — { qId: answerText, ... }
 *   - userName        — captured from the first message before intake
 *   - setUserName     — setter (called by ChatPage when first message arrives)
 *   - startIntake     — pushes intro + first question into the message list,
 *                       then voices them.
 *   - handleIntakeAnswer — handles answer submission, advances or finalises.
 *
 * Caller wires `setMessages` (from useChat), `sendMessage` (final summary),
 * `lang`, and TTS dependencies. This hook owns intake-only state.
 */
export default function useIntakeFlow({
  setMessages,
  sendMessage,
  lang,
  ttsEnabled,
  activeVoice,
  playTTS,
}) {
  const [intakeStep, setIntakeStep] = useState(-1);
  const [intakeAnswers, setIntakeAnswers] = useState({});
  const [userName, setUserName] = useState('');

  const startIntake = useCallback((name) => {
    const introText = getIntakeIntro(lang, name);
    const introMsg = {
      role: 'ai',
      content: introText,
      id: `intake_intro_${Date.now()}`,
    };
    const questions = getIntakeQuestions(lang);
    const firstQ = questions[0];
    const qMsg = {
      role: 'ai',
      content: '',
      id: `intake_${firstQ.id}_${Date.now()}`,
      intakeQuestion: firstQ,
      intakeAnswered: false,
    };
    setMessages((prev) => [...prev, introMsg, qMsg]);
    setIntakeStep(0);
    if (ttsEnabled && activeVoice) {
      setTimeout(() => playTTS(`${introText} ${firstQ.text}`, 0, activeVoice), 150);
    }
  }, [setMessages, lang, ttsEnabled, activeVoice, playTTS]);

  const handleIntakeAnswer = useCallback((qId, answerText, extraFields) => {
    setMessages((prev) => {
      const updated = prev.map((m) =>
        m.intakeQuestion && m.intakeQuestion.id === qId
          ? { ...m, intakeAnswered: true }
          : m
      );
      return [
        ...updated,
        { role: 'user', content: answerText, id: `ans_${qId}_${Date.now()}` },
      ];
    });

    const newAnswers = { ...intakeAnswers, [qId]: answerText, ...(extraFields || {}) };
    setIntakeAnswers(newAnswers);

    const questions = getIntakeQuestions(lang);
    const nextIdx = nextIntakeStep(
      newAnswers,
      questions.findIndex((q) => q.id === qId),
      lang,
    );

    if (nextIdx === -1) {
      const summary = buildIntakeSummary(userName, newAnswers, lang);
      const outroText = getIntakeOutro(lang, userName);
      setIntakeStep(-2);
      setMessages((prev) => [...prev, {
        role: 'ai',
        content: outroText,
        id: `intake_outro_${Date.now()}`,
      }]);
      if (ttsEnabled && activeVoice) {
        setTimeout(() => playTTS(outroText, 0, activeVoice), 150);
      }
      setTimeout(() => sendMessage(summary), 300);
      return;
    }

    const nextQ = questions[nextIdx];
    setMessages((prev) => [...prev, {
      role: 'ai',
      content: '',
      id: `intake_${nextQ.id}_${Date.now()}`,
      intakeQuestion: nextQ,
      intakeAnswered: false,
    }]);
    setIntakeStep(nextIdx);
    if (ttsEnabled && activeVoice) {
      setTimeout(() => playTTS(nextQ.text, 0, activeVoice), 150);
    }
  }, [intakeAnswers, userName, setMessages, sendMessage, lang, ttsEnabled, activeVoice, playTTS]);

  return {
    intakeStep,
    intakeAnswers,
    userName,
    setUserName,
    startIntake,
    handleIntakeAnswer,
  };
}
