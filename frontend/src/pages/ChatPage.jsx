import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import BurgerMenu from '@/components/BurgerMenu';
import ChatHeader from '@/components/chat/ChatHeader';
import ChatInputBar from '@/components/chat/ChatInputBar';
import MessageList from '@/components/chat/MessageList';
import ImagePreview from '@/components/chat/ImagePreview';
import ImagePickerModal from '@/components/chat/ImagePickerModal';
import QuickReplies from '@/components/chat/QuickReplies';
import SpecialistContactModal from '@/components/chat/SpecialistContactModal';
import AuthPromptModal from '@/components/chat/AuthPromptModal';
import useAudioStream from '@/hooks/useAudioStream';
import useChat from '@/hooks/useChat';
import useImageUpload from '@/hooks/useImageUpload';
import useGreetingPreload, { getLangGreeting } from '@/hooks/useGreetingPreload';
import useIntakeFlow from '@/hooks/useIntakeFlow';
import useSpeechCapture from '@/hooks/useSpeechCapture';
import apiClient from '@/lib/apiClient';

export default function ChatPage() {
  const { user, refreshUser, isGuest } = useAuth();
  const { t, lang } = useLanguage();
  const navigate = useNavigate();

  // ---- UI state ----
  const [menuOpen, setMenuOpen] = useState(false);
  const [showSpecialistModal, setShowSpecialistModal] = useState(false);
  const [showAuthPrompt, setShowAuthPrompt] = useState(false);
  const [authPromptShown, setAuthPromptShown] = useState(false);
  const [input, setInput] = useState('');
  const [showImagePicker, setShowImagePicker] = useState(false);
  const [voiceChosen, setVoiceChosen] = useState(false);
  const [activeVoice, setActiveVoice] = useState(null);

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  // Persistent audio element (Xicon pattern — better mobile compatibility).
  const audioElementRef = useRef(null);

  // ---- TTS / chat hooks ----
  const {
    playTTS, stopTTS, playingTTS,
    ttsEnabled, toggleTTS,
    resetTTSQueue, enqueueSentence,
  } = useAudioStream(user, audioElementRef);

  const handleAIMessage = useCallback(() => {
    // Streaming pipeline plays sentences as they arrive — no-op here.
  }, []);

  const ttsBridge = useMemo(
    () => ({ resetTTSQueue, enqueueSentence }),
    [resetTTSQueue, enqueueSentence],
  );

  const {
    messages, sendMessage, loading, sessionId,
    setMessages, historyLoaded, startNewSession, switchVoice,
  } = useChat(user, lang, refreshUser, handleAIMessage, activeVoice, ttsBridge);

  // ---- Greeting MP3 preload (cache for both voices) ----
  const greetingCacheRef = useGreetingPreload({ voiceChosen, lang });

  // ---- Intake flow ----
  const {
    intakeStep, userName, setUserName, startIntake, handleIntakeAnswer,
  } = useIntakeFlow({
    setMessages, sendMessage, lang, ttsEnabled, activeVoice, playTTS,
  });

  // If history loaded with messages, skip voice selection.
  useEffect(() => {
    if (historyLoaded && messages.length > 0 && !voiceChosen) {
      setVoiceChosen(true);
      setActiveVoice(user?.selected_voice || 'female');
    }
  }, [historyLoaded, messages.length, voiceChosen, user?.selected_voice]);

  // Scroll to bottom on new messages.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    const timer = setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 300);
    return () => clearTimeout(timer);
  }, [messages, loading]);

  // Voice selection — first pick OR mid-dialog agent switch.
  const handleVoiceSelect = async (voice) => {
    if (voice === activeVoice) return;

    const isSwitch = voiceChosen && messages.length > 0;
    const prevVoice = activeVoice;
    let restoredHistory = false;
    if (isSwitch) {
      restoredHistory = switchVoice(voice, prevVoice);
      stopTTS();
    }

    setActiveVoice(voice);
    setVoiceChosen(true);

    try {
      await apiClient.put('/user/voice', { voice });
      await refreshUser();
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        // eslint-disable-next-line no-console
        console.error('Voice save failed:', err.message);
      }
    }

    if (isSwitch && restoredHistory) return;

    if (isSwitch && !restoredHistory) {
      const greetingText = getLangGreeting(lang, voice);
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

    // First pick — standard greeting.
    stopTTS();
    const greetingText = getLangGreeting(lang, voice);
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

  // ---- Send handler ----
  const handleSend = useCallback((text) => {
    const msg = text || input;
    if (!msg || !msg.trim() || loading) return;
    const trimmed = msg.trim();

    // Pre-intake: first user message is the name → start intake; do NOT hit backend.
    if (voiceChosen && intakeStep === -1 && !userName) {
      const nameOnly = trimmed.replace(/^(меня зовут|я|это)\s+/i, '').split(/[.,!?\s]/)[0] || trimmed;
      setUserName(nameOnly);
      setMessages(prev => [
        ...prev,
        { role: 'user', content: trimmed, id: `user_name_${Date.now()}` },
      ]);
      setInput('');
      startIntake(nameOnly);
      return;
    }
    sendMessage(trimmed);
    setInput('');
  }, [input, loading, sendMessage, voiceChosen, intakeStep, userName, setUserName, setMessages, startIntake]);

  // ---- Speech capture (mic + waveform + running text) ----
  const {
    isListening, isSupported,
    showRunningText, runningText, handleMicClick,
  } = useSpeechCapture({ lang, stopTTS, onSubmit: handleSend, t });

  // ---- Image upload ----
  const { selectedImage, setSelectedImage, handleImageSelect, sendImageMessage } = useImageUpload({
    sessionId, lang, user, messages, setMessages, refreshUser, ttsEnabled, playTTS, loading,
  });

  // 🔓 Unlimited: ограничения отключены
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

  // B4: Clear chat — wipes server-side messages + UI history; keeps user profile + intake.
  const handleClearChat = useCallback(async () => {
    if (!window.confirm(t('clearChatConfirm'))) return;
    try {
      await apiClient.delete('/chat/messages');
    } catch (err) {
      if (process.env.NODE_ENV === 'development') {
        // eslint-disable-next-line no-console
        console.error('Clear chat failed:', err.message);
      }
    }
    stopTTS();
    startNewSession();
    if (activeVoice) {
      const greetingText = getLangGreeting(lang, activeVoice);
      setMessages([{
        role: 'ai',
        content: greetingText,
        id: `greeting_${activeVoice}_${Date.now()}`,
      }]);
    }
    toast(t('chatCleared'));
  }, [t, stopTTS, startNewSession, activeVoice, lang, setMessages]);

  // B5: After intake — prompt guests to save progress.
  useEffect(() => {
    if (intakeStep === -2 && isGuest && !authPromptShown) {
      const id = setTimeout(() => {
        setShowAuthPrompt(true);
        setAuthPromptShown(true);
      }, 1500);
      return () => clearTimeout(id);
    }
    return undefined;
  }, [intakeStep, isGuest, authPromptShown]);

  // After intake — invite the user to install the PWA. Delayed to not stack with auth prompt.
  const installPromptTriggeredRef = useRef(false);
  useEffect(() => {
    if (intakeStep !== -2 || installPromptTriggeredRef.current) return undefined;
    installPromptTriggeredRef.current = true;
    const id = setTimeout(() => {
      window.dispatchEvent(new Event('miro:show-install-prompt'));
    }, 6000);
    return () => clearTimeout(id);
  }, [intakeStep]);

  // B1: Quick replies visible only after intake completes.
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

        <ChatInputBar
          input={input}
          setInput={setInput}
          onSend={handleSend}
          loading={loading}
          placeholder={t('sendMessage')}
          isListening={isListening}
          isSupported={isSupported}
          onMicClick={handleMicClick}
          showRunningText={showRunningText}
          runningText={runningText}
          onOpenImagePicker={() => setShowImagePicker(true)}
        />
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
