import { useState, useCallback, useRef, useEffect } from 'react';
import apiClient from '@/lib/apiClient';
import { useLanguage } from '@/contexts/LanguageContext';

export default function useChat(user, lang, refreshUser, onAIMessage, activeVoice) {
  const { t } = useLanguage();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const sessionIdRef = useRef(`session_${Date.now()}`);
  const refreshUserRef = useRef(refreshUser);
  const onAIMessageRef = useRef(onAIMessage);
  refreshUserRef.current = refreshUser;
  onAIMessageRef.current = onAIMessage;

  useEffect(() => {
    if (!user || historyLoaded) return;
    let cancelled = false;
    const loadHistory = async () => {
      try {
        const { data } = await apiClient.get('/chat/sessions');
        if (data.sessions?.length > 0) {
          const lastSession = data.sessions[0];
          // Only restore if session is recent (within last hour)
          const lastTime = new Date(lastSession.last_timestamp).getTime();
          const isRecent = (Date.now() - lastTime) < 3600000;
          if (isRecent) {
            sessionIdRef.current = lastSession.session_id;
            const histResp = await apiClient.get(`/chat/history/${lastSession.session_id}`);
            if (histResp.data.messages?.length > 0 && !cancelled) {
              const restored = [];
              for (const m of histResp.data.messages) {
                if (m.user_message) restored.push({ role: 'user', content: m.user_message, id: `hist_u_${restored.length}` });
                if (m.ai_response) restored.push({ role: 'ai', content: m.ai_response, id: `hist_a_${restored.length}` });
              }
              if (restored.length > 0) setMessages(restored);
            }
          }
        }
      } catch {
        if (process.env.NODE_ENV === 'development') console.error('No chat history found');
      }
      if (!cancelled) setHistoryLoaded(true);
    };
    loadHistory();
    return () => { cancelled = true; };
  }, [user, historyLoaded]);

  const sendMessage = useCallback(async (text) => {
    if (!text.trim()) return;
    const userMsg = { role: 'user', content: text, id: `user_${Date.now()}` };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const { data } = await apiClient.post('/chat', {
        message: text,
        session_id: sessionIdRef.current,
        problem: user?.selected_problem,
        language: lang,
        voice: activeVoice || user?.selected_voice || 'female',
      });

      const aiMsg = {
        role: 'ai',
        content: data.message,
        id: `ai_${Date.now()}`,
        isTariffPrompt: data.needs_tariff && data.type === 'tariff_prompt',
      };

      setMessages(prev => {
        const updated = [...prev, aiMsg];
        if (!aiMsg.isTariffPrompt && onAIMessageRef.current) {
          onAIMessageRef.current(data.message, updated.length - 1);
        }
        return updated;
      });
      await refreshUserRef.current();
    } catch (err) {
      console.error('Chat error:', err?.response?.status, err?.response?.data, err?.message);
      // При 401 — автоматически пересоздать гостя и повторить
      if (err.response?.status === 401) {
        try {
          const guestResp = await apiClient.post('/auth/guest', {});
          if (guestResp.data.access_token) {
            localStorage.setItem('access_token', guestResp.data.access_token);
          }
          await refreshUserRef.current();
          // Повторить запрос
          const { data } = await apiClient.post('/chat', {
            message: text,
            session_id: sessionIdRef.current,
            problem: user?.selected_problem,
            language: lang,
            voice: activeVoice || user?.selected_voice || 'female',
          });
          const aiMsg = {
            role: 'ai',
            content: data.message,
            id: `ai_${Date.now()}`,
            isTariffPrompt: data.needs_tariff && data.type === 'tariff_prompt',
          };
          setMessages(prev => {
            const updated = [...prev, aiMsg];
            if (!aiMsg.isTariffPrompt && onAIMessageRef.current) {
              onAIMessageRef.current(data.message, updated.length - 1);
            }
            return updated;
          });
          setLoading(false);
          return;
        } catch (retryErr) {
          if (process.env.NODE_ENV === 'development') console.error('Chat 401 retry failed:', retryErr?.message);
        }
      }
      setMessages(prev => [...prev, {
        role: 'ai',
        content: t('errorTryAgain'),
        id: `err_${Date.now()}`,
      }]);
    } finally {
      setLoading(false);
    }
  }, [user?.selected_problem, user?.selected_voice, lang, activeVoice, t]);

  const startNewSession = useCallback(() => {
    sessionIdRef.current = `session_${Date.now()}`;
    setMessages([]);
    setHistoryLoaded(true);
  }, []);

  return { messages, setMessages, sendMessage, loading, sessionId: sessionIdRef.current, historyLoaded, startNewSession };
}
