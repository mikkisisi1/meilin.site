import { useState, useCallback, useRef, useEffect } from 'react';
import apiClient, { API_BASE, getToken } from '@/lib/apiClient';
import { useLanguage } from '@/contexts/LanguageContext';

// Sentence boundary detector — matches `.`, `!`, `?`, `…` and dialog dash separators,
// but skips abbreviations of length <= 2 chars (e.g., "т.е.", numbered lists already stripped server-side).
const SENTENCE_RE = /([^.!?…]+[.!?…]+)(\s+|$)/g;

function extractCompleteSentences(buffer) {
  // Returns [sentences[], remainder]
  const out = [];
  let lastIndex = 0;
  let m;
  SENTENCE_RE.lastIndex = 0;
  while ((m = SENTENCE_RE.exec(buffer)) !== null) {
    const candidate = m[1].trim();
    // Avoid splitting on tiny abbreviations like "т.е." or "и т.д." — require >= 8 chars for a sentence.
    if (candidate.length >= 8) {
      out.push(candidate);
      lastIndex = m.index + m[0].length;
    }
  }
  return [out, buffer.slice(lastIndex)];
}

export default function useChat(user, lang, refreshUser, onAIMessage, activeVoice, ttsBridge) {
  // ttsBridge: { resetTTSQueue, enqueueSentence } from useAudioStream — optional.
  const { t } = useLanguage();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  // Per-voice independent sessions: { male: 'session_xxx', female: 'session_yyy' }
  const sessionsByVoiceRef = useRef({});
  // Per-voice independent message histories
  const messagesByVoiceRef = useRef({});
  const activeVoiceRef = useRef(activeVoice);
  activeVoiceRef.current = activeVoice;
  const refreshUserRef = useRef(refreshUser);
  const onAIMessageRef = useRef(onAIMessage);
  const ttsBridgeRef = useRef(ttsBridge);
  refreshUserRef.current = refreshUser;
  onAIMessageRef.current = onAIMessage;
  ttsBridgeRef.current = ttsBridge;

  const getOrCreateSession = useCallback((voice) => {
    const v = voice || 'female';
    if (!sessionsByVoiceRef.current[v]) {
      sessionsByVoiceRef.current[v] = `session_${v}_${Date.now()}`;
    }
    return sessionsByVoiceRef.current[v];
  }, []);

  // Switch active voice — swap visible messages with that voice's history.
  // prevVoice MUST be passed explicitly because the caller may have already updated activeVoice state
  // before this runs (e.g. across an await), which would make activeVoiceRef.current stale.
  const switchVoice = useCallback((newVoice, prevVoice) => {
    const fromVoice = prevVoice || activeVoiceRef.current;
    if (fromVoice && fromVoice !== newVoice) {
      messagesByVoiceRef.current[fromVoice] = messages;
    }
    const stored = messagesByVoiceRef.current[newVoice];
    if (Array.isArray(stored) && stored.length > 0) {
      setMessages(stored);
      return true; // history restored
    }
    setMessages([]);
    getOrCreateSession(newVoice);
    return false; // no stored history
  }, [messages, getOrCreateSession]);

  useEffect(() => {
    if (!user || historyLoaded) return;
    let cancelled = false;
    const loadHistory = async () => {
      try {
        const { data } = await apiClient.get('/chat/sessions');
        if (data.sessions?.length > 0) {
          const lastSession = data.sessions[0];
          const lastTime = new Date(lastSession.last_timestamp).getTime();
          const isRecent = (Date.now() - lastTime) < 3600000;
          if (isRecent) {
            const histResp = await apiClient.get(`/chat/history/${lastSession.session_id}`);
            if (histResp.data.messages?.length > 0 && !cancelled) {
              const restored = [];
              const restoredVoice = histResp.data.messages[histResp.data.messages.length - 1]?.voice
                || activeVoiceRef.current
                || 'female';
              for (const m of histResp.data.messages) {
                if (m.user_message) restored.push({ role: 'user', content: m.user_message, id: `hist_u_${restored.length}` });
                if (m.ai_response) restored.push({ role: 'ai', content: m.ai_response, id: `hist_a_${restored.length}` });
              }
              if (restored.length > 0) {
                sessionsByVoiceRef.current[restoredVoice] = lastSession.session_id;
                messagesByVoiceRef.current[restoredVoice] = restored;
                if (activeVoiceRef.current === restoredVoice) {
                  setMessages(restored);
                }
              }
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
    const voice = activeVoiceRef.current || user?.selected_voice || 'female';
    const sessionId = getOrCreateSession(voice);
    const userMsg = { role: 'user', content: text, id: `user_${Date.now()}` };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    const aiMsgId = `ai_${Date.now()}`;
    let aiMsgIndexAtAppend = -1;
    let pushedAiMsg = false;
    let buffer = '';
    let pendingTail = '';
    const bridge = ttsBridgeRef.current;

    // Append empty AI message that will be filled with streaming deltas.
    const ensureAiMsg = () => {
      if (pushedAiMsg) return;
      pushedAiMsg = true;
      setMessages(prev => {
        aiMsgIndexAtAppend = prev.length;
        if (bridge?.resetTTSQueue) bridge.resetTTSQueue(aiMsgIndexAtAppend, voice);
        return [...prev, { role: 'ai', content: '', id: aiMsgId }];
      });
    };

    const updateAiContent = (full) => {
      setMessages(prev => prev.map(m => m.id === aiMsgId ? { ...m, content: full } : m));
    };

    const flushSentencesFromBuffer = () => {
      const [complete, rest] = extractCompleteSentences(pendingTail);
      pendingTail = rest;
      if (complete.length && bridge?.enqueueSentence) {
        for (const s of complete) bridge.enqueueSentence(s, voice);
      }
    };

    try {
      const token = getToken();
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
          problem: user?.selected_problem,
          language: lang,
          voice,
        }),
      });

      if (!response.ok || !response.body) {
        // Surface 401 to retry handler below.
        if (response.status === 401) throw Object.assign(new Error('unauthorized'), { status: 401 });
        throw new Error(`stream failed: ${response.status}`);
      }

      ensureAiMsg();
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let sseRemainder = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        sseRemainder += decoder.decode(value, { stream: true });
        const events = sseRemainder.split('\n\n');
        sseRemainder = events.pop() || '';
        for (const evt of events) {
          const line = evt.split('\n').find(l => l.startsWith('data:'));
          if (!line) continue;
          const json = line.slice(5).trim();
          if (!json) continue;
          let payload;
          try { payload = JSON.parse(json); } catch { continue; }
          if (payload.type === 'delta' && payload.text) {
            buffer += payload.text;
            pendingTail += payload.text;
            updateAiContent(buffer);
            flushSentencesFromBuffer();
          } else if (payload.type === 'replace' && typeof payload.text === 'string') {
            // Search-tool result replaced the partial text.
            buffer = payload.text;
            pendingTail = '';
            updateAiContent(buffer);
            // Reset queue and enqueue full text as sentences.
            if (bridge?.resetTTSQueue) bridge.resetTTSQueue(aiMsgIndexAtAppend, voice);
            const [allSentences, remainder] = extractCompleteSentences(buffer + ' ');
            if (bridge?.enqueueSentence) {
              for (const s of allSentences) bridge.enqueueSentence(s, voice);
              const tail = remainder.trim();
              if (tail) bridge.enqueueSentence(tail, voice);
            }
          } else if (payload.type === 'done') {
            // Flush any leftover tail as final sentence.
            const tail = pendingTail.trim();
            if (tail && bridge?.enqueueSentence) bridge.enqueueSentence(tail, voice);
            pendingTail = '';
            if (typeof payload.full_text === 'string') {
              buffer = payload.full_text;
              updateAiContent(buffer);
            }
          } else if (payload.type === 'tariff_prompt') {
            ensureAiMsg();
            buffer = payload.message || '';
            updateAiContent(buffer);
            setMessages(prev => prev.map(m => m.id === aiMsgId ? { ...m, isTariffPrompt: true } : m));
          } else if (payload.type === 'error') {
            throw new Error(payload.message || 'stream error');
          }
        }
      }
      // Cache for per-voice swap
      messagesByVoiceRef.current[voice] = (messagesByVoiceRef.current[voice] || []);
      // Persist by reading state via callback to avoid stale closure.
      setMessages(prev => {
        messagesByVoiceRef.current[voice] = prev;
        return prev;
      });
      try { await refreshUserRef.current?.(); } catch { /* noop */ }
    } catch (err) {
      // 401 retry: register guest and redo via streaming
      if (err?.status === 401) {
        try {
          const guestResp = await apiClient.post('/auth/guest', {});
          if (guestResp.data.access_token) {
            localStorage.setItem('access_token', guestResp.data.access_token);
          }
          await refreshUserRef.current?.();
          setMessages(prev => prev.filter(m => m.id !== aiMsgId));
          setLoading(false);
          // Retry once
          return sendMessage(text);
        } catch (retryErr) {
          if (process.env.NODE_ENV === 'development') console.error('Stream 401 retry failed:', retryErr?.message);
        }
      }
      console.error('Stream chat error:', err?.message);
      // Replace pending empty AI bubble (if any) with error text.
      setMessages(prev => {
        const hasPending = prev.some(m => m.id === aiMsgId);
        if (hasPending) return prev.map(m => m.id === aiMsgId ? { ...m, content: t('errorTryAgain') } : m);
        return [...prev, { role: 'ai', content: t('errorTryAgain'), id: `err_${Date.now()}` }];
      });
    } finally {
      setLoading(false);
    }
  }, [user?.selected_problem, user?.selected_voice, lang, t, getOrCreateSession]);

  const startNewSession = useCallback(() => {
    const voice = activeVoiceRef.current || user?.selected_voice || 'female';
    sessionsByVoiceRef.current[voice] = `session_${voice}_${Date.now()}`;
    messagesByVoiceRef.current[voice] = [];
    setMessages([]);
    setHistoryLoaded(true);
  }, [user?.selected_voice]);

  return {
    messages,
    setMessages,
    sendMessage,
    loading,
    sessionId: activeVoice ? sessionsByVoiceRef.current[activeVoice] : null,
    historyLoaded,
    startNewSession,
    switchVoice,
  };
}
