import { useState, useCallback, useRef, useEffect } from 'react';
import { API_BASE } from '@/lib/apiClient';
import { useLanguage } from '@/contexts/LanguageContext';

function getSpeechAPI() {
  if (typeof window === 'undefined') return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

export const useSpeechRecognition = (language = 'ru') => {
  const { t } = useLanguage();
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isSupported] = useState(() => {
    if (typeof window === 'undefined') return false;
    // Поддержка: либо Web Speech API, либо MediaRecorder (Whisper fallback)
    return !!getSpeechAPI() || !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  });
  
  const recognitionRef = useRef(null);
  const languageRef = useRef(language);
  const modeRef = useRef(null); // 'native' | 'whisper'
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  useEffect(() => {
    languageRef.current = language;
  }, [language]);

  // === Web Speech API (Xicon pattern) ===
  const startNative = useCallback(() => {
    const API = getSpeechAPI();
    const recognition = new API();
    recognitionRef.current = recognition;
    modeRef.current = 'native';
    
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    
    const langMap = {
      'ru': 'ru-RU', 'en': 'en-US', 'uk': 'uk-UA',
      'de': 'de-DE', 'fr': 'fr-FR', 'es': 'es-ES', 'id': 'id-ID',
      'zh': 'zh-CN', 'ar': 'ar-SA', 'hi': 'hi-IN',
    };
    recognition.lang = langMap[languageRef.current] || 'ru-RU';

    let finalText = '';
    let interimText = '';

    recognition.onresult = (event) => {
      finalText = '';
      interimText = '';
      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i];
        const text = result[0].transcript;
        if (result.isFinal) finalText += text;
        else interimText += text;
      }
      setTranscript(finalText || interimText);
    };

    recognition.onerror = (event) => {
      console.error('[STT] Ошибка:', event.error);
      if (event.error === 'not-allowed') {
        alert(t('micDenied'));
      }
      setIsListening(false);
    };

    recognition.onend = () => setIsListening(false);
    recognition.onstart = () => setIsListening(true);

    try {
      recognition.start();
    } catch (e) {
      console.error('[STT] Ошибка запуска:', e);
      setIsListening(false);
    }
  }, [t]);

  // === Whisper fallback (MediaRecorder → /api/stt) ===
  const startWhisper = useCallback(async () => {
    modeRef.current = 'whisper';
    chunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      setIsListening(true);

      let mimeType = 'audio/webm;codecs=opus';
      if (typeof MediaRecorder !== 'undefined' && !MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm'
          : MediaRecorder.isTypeSupported('audio/mp4') ? 'audio/mp4' : '';
      }

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        streamRef.current = null;

        const blob = new Blob(chunksRef.current, { type: mimeType || 'audio/webm' });
        if (blob.size < 100) { setIsListening(false); return; }

        try {
          const formData = new FormData();
          const ext = mimeType.includes('mp4') ? 'mp4' : 'webm';
          formData.append('audio', blob, 'recording.' + ext);
          formData.append('language', languageRef.current || 'ru');

          const res = await fetch(API_BASE + '/stt', {
            method: 'POST',
            body: formData,
          });

          if (res.ok) {
            const data = await res.json();
            if (data.text && data.text.trim()) setTranscript(data.text.trim());
          }
        } catch (err) {
          console.error('[STT] Whisper error:', err);
        }
        setIsListening(false);
      };

      recorder.onerror = () => {
        setIsListening(false);
        stream.getTracks().forEach(t => t.stop());
      };

      recorder.start();
    } catch (err) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        alert(t('micDenied'));
      } else {
        alert(t('micUnavailable'));
      }
      setIsListening(false);
    }
  }, [t]);

  // === Public API ===
  const startListening = useCallback(() => {
    if (isListening) return;

    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch (err) {
        if (process.env.NODE_ENV === 'development') console.debug('[STT] abort ignored:', err?.message);
      }
    }
    setTranscript('');

    // Сначала пробуем Web Speech API, потом Whisper fallback
    if (getSpeechAPI()) {
      startNative();
    } else if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      startWhisper();
    } else {
      alert(t('browserNoSpeech'));
    }
  }, [isListening, startNative, startWhisper, t]);

  const stopListening = useCallback(() => {
    if (modeRef.current === 'native' && recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (err) {
        if (process.env.NODE_ENV === 'development') console.debug('[STT] stop ignored:', err?.message);
      }
    }
    if (modeRef.current === 'whisper' && mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try { mediaRecorderRef.current.stop(); } catch (err) {
        if (process.env.NODE_ENV === 'development') console.debug('[STT] recorder stop ignored:', err?.message);
      }
      return; // onstop обработает setIsListening(false)
    }
    setIsListening(false);
  }, []);

  return { 
    isListening, 
    transcript, 
    isSupported, 
    startListening, 
    stopListening 
  };
};

export default useSpeechRecognition;
