import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Mic, Camera } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { getGreeting } from '@/contexts/translations-extra';
import BurgerMenu from '@/components/BurgerMenu';
import ChatHeader from '@/components/chat/ChatHeader';
import MessageList from '@/components/chat/MessageList';
import ImagePreview from '@/components/chat/ImagePreview';
import ImagePickerModal from '@/components/chat/ImagePickerModal';
import QuickReplies from '@/components/chat/QuickReplies';
import SpecialistContactModal from '@/components/chat/SpecialistContactModal';
import AuthPromptModal from '@/components/chat/AuthPromptModal';
import useAudioStream from '@/hooks/useAudioStream';
import useChat from '@/hooks/useChat';
import useSpeechRecognition from '@/hooks/useSpeechRecognition';
import useImageUpload from '@/hooks/useImageUpload';
import apiClient, { API_BASE } from '@/lib/apiClient';
import { getIntakeQuestions, getIntakeIntro, getIntakeOutro, nextIntakeStep, buildIntakeSummary } from '@/config/intakeQuestions';

const GREETINGS = {
  male: "Hi, I'm Leon — I'm here to support you.\nHow are you feeling today?",
  female: "Hi, I'm Kylie — I'm here to support you.\nHow are you feeling today?",
};

const getLangGreeting = (lang, voice) => getGreeting(lang, voice) || GREETINGS[voice];

export default function ChatPage() {
  const { user, refreshUser, isGuest } = useAuth();
  const { t, lang } = useLanguage();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [showSpecialistModal, setShowSpecialistModal] = useState(false);
  const [showAuthPrompt, setShowAuthPrompt] = useState(false);
  const [authPromptShown, setAuthPromptShown] = useState(false);
  const [input, setInput] = useState('');
  const [showImagePicker, setShowImagePicker] = useState(false);
  const [voiceChosen, setVoiceChosen] = useState(false);
  const [activeVoice, setActiveVoice] = useState(null);
  const [showRunningText, setShowRunningText] = useState(false);
  const [runningText, setRunningText] = useState('');
  // Intake flow state
  const [intakeStep, setIntakeStep] = useState(-1); // -1 = not started, 0..N = Qi, -2 = done
  const [intakeAnswers, setIntakeAnswers] = useState({});
  const [userName, setUserName] = useState('');
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  const greetingCacheRef = useRef({ male: null, female: null });
  const silenceTimerRef = useRef(null);
  const lastTranscriptRef = useRef('');

  // Persistent audio element ref (like Xicon) — better mobile compatibility
  const audioElementRef = useRef(null);

  const { playTTS, stopTTS, playingTTS, ttsEnabled, toggleTTS, resetTTSQueue, enqueueSentence } = useAudioStream(user, audioElementRef);

  const handleAIMessage = useCallback(() => {
    // Streaming pipeline plays sentences as they arrive — no-op here.
    // Kept to satisfy useChat hook signature.
  }, []);

  const ttsBridge = useMemo(
    () => ({ resetTTSQueue, enqueueSentence }),
    [resetTTSQueue, enqueueSentence]
  );

  const { messages, sendMessage, loading, sessionId, setMessages, historyLoaded, startNewSession, switchVoice } = useChat(user, lang, refreshUser, handleAIMessage, activeVoice, ttsBridge);

  // If history loaded with messages, skip voice selection
  useEffect(() => {
    if (historyLoaded && messages.length > 0 && !voiceChosen) {
      setVoiceChosen(true);
      setActiveVoice(user?.selected_voice || 'female');
    }
  }, [historyLoaded, messages.length, voiceChosen, user?.selected_voice]);

  // Pre-cache greeting TTS audio for both voices — для текущего языка интерфейса
  useEffect(() => {
    if (voiceChosen) return;
    let cancelled = false;

    const preloadGreeting = async (voice) => {
      try {
        const text = getGreeting(lang, voice) || GREETINGS[voice];
        const response = await fetch(`${API_BASE}/tts`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ text, voice }),
        });
        if (response.ok && !cancelled) {
          const blob = await response.blob();
          if (!cancelled) greetingCacheRef.current[voice] = URL.createObjectURL(blob);
        }
      } catch (err) {
        if (process.env.NODE_ENV === 'development') console.error('TTS greeting cache miss:', err.message);
      }
    };
    preloadGreeting('male');
    preloadGreeting('female');

    return () => {
      cancelled = true;
      // Invalidate cache when lang changes before voice is chosen
      greetingCacheRef.current = { male: null, female: null };
    };
  }, [voiceChosen, lang]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    const timer = setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 300);
    return () => clearTimeout(timer);
  }, [messages, loading]);

  // Voice selection handler — первый выбор ИЛИ переключение агента.
  // При переключении подменяем историю чата на ту, что хранится для выбранного агента.
  const handleVoiceSelect = async (voice) => {    // Клик по уже активному агенту — ничего не делаем.
    if (voice === activeVoice) return;

    const isSwitch = voiceChosen && messages.length > 0;
    const prevVoice = activeVoice; // снимок ДО любого await
    let restoredHistory = false;
    if (isSwitch) {
      // Сохраняем историю текущего агента и подменяем на сохранённую историю выбранного — синхронно, до await.
      restoredHistory = switchVoice(voice, prevVoice);
      stopTTS();
    }

    setActiveVoice(voice);
    setVoiceChosen(true);

    try {
      await apiClient.put('/user/voice', { voice });
      await refreshUser();
    } catch (err) {
      if (process.env.NODE_ENV === 'development') console.error('Voice save failed:', err.message);
    }

    if (isSwitch && restoredHistory) {
      // У нового агента уже есть история — ничего больше не делаем.
      return;
    }

    if (isSwitch && !restoredHistory) {
      // У нового агента истории нет — посеять приветствие.
      const greetingText = getGreeting(lang, voice) || GREETINGS[voice];
      setMessages([{
        role: 'ai',
        content: greetingText,
        id: `greeting_${voice}_${Date.now()}`,
      }]);
      if (ttsEnabled) {
        setTimeout(() => playTTS(greetingText, 0, voice), 100);
      }
      return;
    }

    // Первый выбор агента — стандартное приветствие.
    stopTTS();
    const greetingText = getGreeting(lang, voice) || GREETINGS[voice];
    setMessages([{
      role: 'ai',
      content: greetingText,
      id: `greeting_${voice}_${Date.now()}`,
    }]);

    const cachedUrl = greetingCacheRef.current[voice];
    if (cachedUrl && audioElementRef.current) {
      const audio = audioElementRef.current;
      audio.src = cachedUrl;
      audio.play().catch(() => {});
    } else if (ttsEnabled) {
      setTimeout(() => playTTS(greetingText, 0, voice), 100);
    }
  };

  // Text sending
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
    // Voice intro + first question text in user's language.
    if (ttsEnabled && activeVoice) {
      setTimeout(() => playTTS(`${introText} ${firstQ.text}`, 0, activeVoice), 150);
    }
  }, [setMessages, lang, ttsEnabled, activeVoice, playTTS]);

  const handleIntakeAnswer = useCallback((qId, answerText, extraFields) => {
    // Mark the current question message as answered and append user's answer.
    setMessages((prev) => {
      const updated = prev.map((m) =>
        m.intakeQuestion && m.intakeQuestion.id === qId ? { ...m, intakeAnswered: true } : m
      );
      return [...updated, { role: 'user', content: answerText, id: `ans_${qId}_${Date.now()}` }];
    });

    const newAnswers = { ...intakeAnswers, [qId]: answerText, ...(extraFields || {}) };
    setIntakeAnswers(newAnswers);

    const questions = getIntakeQuestions(lang);
    const nextIdx = nextIntakeStep(newAnswers, questions.findIndex((q) => q.id === qId), lang);
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
    } else {
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
    }
  }, [intakeAnswers, userName, setMessages, sendMessage, lang, ttsEnabled, activeVoice, playTTS]);

  const handleSend = useCallback((text) => {
    const msg = text || input;
    if (!msg || !msg.trim() || loading) return;
    const trimmed = msg.trim();
    // Before intake starts: first user message = name → trigger intake, do NOT hit backend.
    if (voiceChosen && intakeStep === -1 && !userName) {
      const nameOnly = trimmed.replace(/^(меня зовут|я|это)\s+/i, '').split(/[.,!?\s]/)[0] || trimmed;
      setUserName(nameOnly);
      setMessages((prev) => [...prev, { role: 'user', content: trimmed, id: `user_name_${Date.now()}` }]);
      setInput('');
      startIntake(nameOnly);
      return;
    }
    sendMessage(trimmed);
    setInput('');
  }, [input, loading, sendMessage, voiceChosen, intakeStep, userName, setMessages, startIntake]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Speech recognition — ТОЧНАЯ КОПИЯ из Xicon.online
  const { isListening, transcript, isSupported, startListening, stopListening } = useSpeechRecognition(lang);

  // Логика паузы 3 сек — показать бегущую строку (из Xicon)
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

  // Сброс при остановке записи (из Xicon)
  useEffect(() => {
    if (!isListening && !transcript) {
      setShowRunningText(false);
      setRunningText('');
      lastTranscriptRef.current = '';
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    }
  }, [isListening, transcript]);

  // Когда распознавание завершено — показать бегущую строку и отправить (из Xicon)
  const sentTranscriptRef = useRef('');
  useEffect(() => {
    if (!isListening && transcript && transcript.trim() && transcript !== sentTranscriptRef.current) {
      sentTranscriptRef.current = transcript;
      setRunningText(transcript);
      setShowRunningText(true);
      handleSend(transcript);
      const hideTimer = setTimeout(() => {
        setShowRunningText(false);
        setRunningText('');
        sentTranscriptRef.current = '';
      }, 8000);
      return () => clearTimeout(hideTimer);
    }
  }, [isListening, transcript, handleSend]);

  // handleMicClick — ТОЧНАЯ КОПИЯ из Xicon.online
  const handleMicClick = useCallback(() => {
    if (!isSupported) {
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

  // Image upload
  const { selectedImage, setSelectedImage, handleImageSelect, sendImageMessage } = useImageUpload({
    sessionId, lang, user, messages, setMessages, refreshUser, ttsEnabled, playTTS, loading,
  });

  // 🔓 Безлимит: ограничения отключены
  const minutesLeft = 999;
  const isFreePhase = true;
  const hasMinutes = true;
  const countdownSeconds = null;
  const formatTime = (mins) => {
    if (mins >= 60) return `${Math.floor(mins / 60)}${t('hours')} ${mins % 60}${t('min')}`;
    return `${mins} ${t('min')}`;
  };

  const isDesktop = typeof window !== 'undefined' && window.innerWidth >= 769;
  const chatBg = isDesktop
    ? `${process.env.PUBLIC_URL}/chat-bg-desktop.jpg`
    : `${process.env.PUBLIC_URL}/chat-bg.jpg`;

  // B4: Clear chat — wipes server-side messages + UI history; keeps user profile + questionnaire.
  const handleClearChat = useCallback(async () => {
    if (!window.confirm(t('clearChatConfirm'))) return;
    try {
      await apiClient.delete('/chat/messages');
    } catch (err) {
      if (process.env.NODE_ENV === 'development') console.error('Clear chat failed:', err.message);
    }
    stopTTS();
    startNewSession();
    if (activeVoice) {
      const greetingText = getGreeting(lang, activeVoice) || GREETINGS[activeVoice];
      setMessages([{
        role: 'ai',
        content: greetingText,
        id: `greeting_${activeVoice}_${Date.now()}`,
      }]);
    }
    toast(t('chatCleared'));
  }, [t, stopTTS, startNewSession, activeVoice, lang, setMessages]);

  // B5: After intake is complete — prompt guest users to save their progress.
  useEffect(() => {
    if (intakeStep === -2 && isGuest && !authPromptShown) {
      const id = setTimeout(() => {
        setShowAuthPrompt(true);
        setAuthPromptShown(true);
      }, 1500);
      return () => clearTimeout(id);
    }
  }, [intakeStep, isGuest, authPromptShown]);

  // After intake is complete — invite the user to install the PWA.
  // Fires once per session, gated 7d via DISMISS_KEY in InstallPrompt itself.
  // Delay is intentionally longer than the AuthPromptModal (1.5s) so the two
  // don't stack: by the time this fires, guests have already engaged with auth.
  const installPromptTriggeredRef = useRef(false);
  useEffect(() => {
    if (intakeStep !== -2 || installPromptTriggeredRef.current) return;
    installPromptTriggeredRef.current = true;
    const id = setTimeout(() => {
      window.dispatchEvent(new Event('miro:show-install-prompt'));
    }, 6000);
    return () => clearTimeout(id);
  }, [intakeStep]);

  // B1: Quick replies visible only after intake completes (so they don't conflict with name/intake prompts).
  const isIntakePending = messages.some((m) => m.intakeQuestion && !m.intakeAnswered);
  const showQuickReplies = (
    voiceChosen
    && intakeStep === -2
    && !isIntakePending
    && !loading
    && !isListening
    && !showRunningText
    && !input.trim()
  );

  return (
    <div className="xc-chat-modal" data-testid="chat-page">
      <div className="xc-chat-bg" style={{ backgroundImage: `url(${chatBg})` }} />

      {/* Persistent audio element for TTS (Xicon pattern — better mobile compatibility) */}
      <audio ref={audioElementRef} playsInline preload="none" style={{ display: 'none' }} />

      <ChatHeader
        voiceChosen={voiceChosen}
        activeVoice={activeVoice}
        onVoiceSelect={handleVoiceSelect}
        ttsEnabled={ttsEnabled}
        toggleTTS={toggleTTS}
        isFreePhase={isFreePhase}
        hasMinutes={hasMinutes}
        minutesLeft={minutesLeft}
        formatTime={formatTime}
        onBack={() => navigate('/')}
        onMenuOpen={() => setMenuOpen(true)}
        freeSessionLabel={t('freeSession')}
        countdownSeconds={countdownSeconds}
        isBusy={loading || playingTTS}
        onClearChat={handleClearChat}
      />

      <div className="xc-chat-body">
        <div className="xc-chat-messages" data-testid="chat-messages">
          {!voiceChosen && messages.length === 0 && (
            <div className="xc-voice-hint" data-testid="voice-hint">
              <p>{t('chooseVoice')}</p>
            </div>
          )}
          <MessageList
            messages={messages}
            loading={loading}
            playingTTS={playingTTS}
            playTTS={playTTS}
            stopTTS={stopTTS}
            messagesEndRef={messagesEndRef}
            activeVoice={activeVoice}
            onIntakeAnswer={handleIntakeAnswer}
          />
        </div>

        <ImagePreview
          selectedImage={selectedImage}
          onRemove={() => setSelectedImage(null)}
          onSend={sendImageMessage}
          loading={loading}
        />

        <input type="file" ref={fileInputRef} accept="image/*" onChange={handleImageSelect} style={{ display: 'none' }} />
        <input type="file" ref={cameraInputRef} accept="image/*" capture="environment" onChange={handleImageSelect} style={{ display: 'none' }} />

        {showQuickReplies && (
          <QuickReplies onPick={(text) => handleSend(text)} disabled={loading} />
        )}

        {/* Input Area — inline как в Xicon.online App.js */}
        <div className="xc-chat-input-area" data-testid="chat-input-form">
          <div className="xc-input-container">
            {showRunningText && runningText ? (
              <span className="xc-running-text-inner">{runningText}</span>
            ) : isListening ? (
              <div className="xc-wave-inner">
                <svg viewBox="0 0 320 30" preserveAspectRatio="none">
                  <path className="xc-wave-path-1" d="M0,15 Q20,5 40,15 Q60,25 80,15 Q100,5 120,15 Q140,25 160,15 Q180,5 200,15 Q220,25 240,15 Q260,5 280,15 Q300,25 320,15" />
                  <path className="xc-wave-path-2" d="M0,15 Q20,25 40,15 Q60,5 80,15 Q100,25 120,15 Q140,5 160,15 Q180,25 200,15 Q220,5 240,15 Q260,25 280,15 Q300,5 320,15" />
                </svg>
              </div>
            ) : (
              <input
                data-testid="chat-input"
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder={t('sendMessage')}
                className="xc-chat-text-input-inner"
                disabled={loading}
              />
            )}
            {!isListening && !showRunningText && (
              <button
                className="xc-camera-inline-btn"
                data-testid="camera-inline-btn"
                onClick={() => setShowImagePicker(true)}
                disabled={loading}
              >
                <Camera size={19} strokeWidth={1.5} />
              </button>
            )}
          </div>

          {!isListening && !showRunningText && (
            <button
              data-testid="send-btn"
              onClick={() => handleSend()}
              disabled={!input.trim() || loading}
              className="xc-send-btn"
            >
              <Send size={16} strokeWidth={1.5} />
            </button>
          )}

          <button
            className={`xc-mic-btn ${isListening ? 'recording' : ''}`}
            onClick={handleMicClick}
            disabled={loading || !isSupported}
            data-testid="mic-btn"
            aria-label={isListening ? "Stop recording" : "Start recording"}
          >
            <Mic size={20} strokeWidth={1.5} />
          </button>
        </div>
      </div>

      {showImagePicker && (
        <ImagePickerModal
          onClose={() => setShowImagePicker(false)}
          onCamera={() => cameraInputRef.current?.click()}
          onGallery={() => fileInputRef.current?.click()}
        />
      )}

      <BurgerMenu
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        onTalkToSpecialist={() => setShowSpecialistModal(true)}
      />

      <SpecialistContactModal
        open={showSpecialistModal}
        onClose={() => setShowSpecialistModal(false)}
      />

      <AuthPromptModal
        open={showAuthPrompt}
        onClose={() => setShowAuthPrompt(false)}
      />
    </div>
  );
}
