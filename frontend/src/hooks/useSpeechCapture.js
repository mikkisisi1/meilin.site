import { useEffect, useRef, useState, useCallback } from 'react';
import useSpeechRecognition from '@/hooks/useSpeechRecognition';

/**
 * Owns mic capture UX:
 *   - Wraps useSpeechRecognition.
 *   - Shows a 3-second silence "running text" preview of the live transcript.
 *   - When the user stops (or recognizer ends naturally), forwards the final
 *     transcript to `onSubmit` and keeps it visible on screen for 8s.
 *   - Implements barge-in: starting the mic stops any current TTS playback,
 *     so the recognizer doesn't capture the AI's own voice.
 *
 * Returns everything ChatPage needs to render the input area.
 */
export default function useSpeechCapture({ lang, stopTTS, onSubmit, t }) {
  const [showRunningText, setShowRunningText] = useState(false);
  const [runningText, setRunningText] = useState('');
  const silenceTimerRef = useRef(null);
  const lastTranscriptRef = useRef('');
  const sentTranscriptRef = useRef('');

  const {
    isListening,
    transcript,
    isSupported,
    startListening,
    stopListening,
  } = useSpeechRecognition(lang);

  // Silence-detection: after 3s of no transcript change, surface the running text.
  useEffect(() => {
    if (isListening && transcript) {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      if (transcript !== lastTranscriptRef.current) {
        lastTranscriptRef.current = transcript;
        setShowRunningText(false);
        silenceTimerRef.current = setTimeout(() => {
          if (transcript && transcript.trim()) {
            setRunningText(transcript);
            setShowRunningText(true);
          }
        }, 3000);
      }
    }
    return () => {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    };
  }, [isListening, transcript]);

  // Reset on stop.
  useEffect(() => {
    if (!isListening && !transcript) {
      setShowRunningText(false);
      setRunningText('');
      lastTranscriptRef.current = '';
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    }
  }, [isListening, transcript]);

  // On final transcript — show + send + auto-hide after 8s.
  useEffect(() => {
    if (
      !isListening
      && transcript
      && transcript.trim()
      && transcript !== sentTranscriptRef.current
    ) {
      sentTranscriptRef.current = transcript;
      setRunningText(transcript);
      setShowRunningText(true);
      onSubmit(transcript);
      const hideTimer = setTimeout(() => {
        setShowRunningText(false);
        setRunningText('');
        sentTranscriptRef.current = '';
      }, 8000);
      return () => clearTimeout(hideTimer);
    }
    return undefined;
  }, [isListening, transcript, onSubmit]);

  const handleMicClick = useCallback(() => {
    if (!isSupported) {
      // eslint-disable-next-line no-alert
      alert(t('browserNoSpeech'));
      return;
    }
    if (isListening) {
      stopListening();
    } else {
      // Barge-in: silence Leon/Kylie the moment the user wants to talk —
      // otherwise TTS keeps playing over the mic and gets re-captured by STT.
      stopTTS();
      startListening();
    }
  }, [isSupported, isListening, startListening, stopListening, stopTTS, t]);

  return {
    isListening,
    isSupported,
    showRunningText,
    runningText,
    handleMicClick,
  };
}
