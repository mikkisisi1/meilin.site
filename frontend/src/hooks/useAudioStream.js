import { useState, useRef, useCallback } from 'react';
import { API_BASE, getToken } from '@/lib/apiClient';

/**
 * TTS playback hook with streaming via MediaSource Extensions where supported.
 * Audio starts playing as soon as the first MP3 chunk arrives from backend
 * (~300ms TTFB with Fish Audio `latency=balanced`).
 *
 * Fallback: if MediaSource or `audio/mpeg` is not supported (iOS Safari)
 * OR the MSE pipeline fails mid-stream → buffer into a Blob and play normally.
 *
 * Sentence queue API for streaming TTS:
 *   resetTTSQueue(msgIndex, voice)  — start a new queue for an AI message
 *   enqueueSentence(sentence)        — push a sentence; plays sequentially
 */
export default function useAudioStream(user, audioElementRef) {
  const [playingTTS, setPlayingTTS] = useState(null);
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const cancelledRef = useRef(false);
  const abortRef = useRef(null);
  const currentUrlRef = useRef(null);

  // ---- Streaming sentence queue state ----
  const queueRef = useRef([]);
  const queueActiveRef = useRef(false);
  const queueMsgIndexRef = useRef(null);
  const queueVoiceRef = useRef(null);
  const queueAbortRef = useRef(null);

  const clearAudioHandlers = useCallback(() => {
    const audio = audioElementRef?.current;
    if (!audio) return;
    audio.onended = null;
    audio.onerror = null;
  }, [audioElementRef]);

  const revokeCurrentUrl = useCallback(() => {
    if (currentUrlRef.current) {
      try { URL.revokeObjectURL(currentUrlRef.current); } catch { /* noop */ }
      currentUrlRef.current = null;
    }
  }, []);

  const stopTTS = useCallback(() => {
    cancelledRef.current = true;
    if (abortRef.current) {
      try { abortRef.current.abort(); } catch { /* noop */ }
      abortRef.current = null;
    }
    if (queueAbortRef.current) {
      try { queueAbortRef.current.abort(); } catch { /* noop */ }
      queueAbortRef.current = null;
    }
    queueRef.current = [];
    queueActiveRef.current = false;
    queueMsgIndexRef.current = null;
    queueVoiceRef.current = null;
    const audio = audioElementRef?.current;
    if (audio) {
      clearAudioHandlers();
      try {
        audio.pause();
        audio.removeAttribute('src');
        audio.load();
      } catch { /* noop */ }
    }
    revokeCurrentUrl();
    setPlayingTTS(null);
  }, [audioElementRef, clearAudioHandlers, revokeCurrentUrl]);

  const toggleTTS = useCallback(() => {
    setTtsEnabled(prev => {
      if (prev) stopTTS();
      return !prev;
    });
  }, [stopTTS]);

  // ---- Streaming sentence queue: fetch one sentence as MP3, play, then drain ----
  // queueRef stores tuples: { sentence, voice } — voice is captured per-sentence
  // to guarantee Leon/Kylie voices NEVER cross even if state changes mid-stream.
  const playNextInQueue = useCallback(async () => {
    if (cancelledRef.current) return;
    if (queueActiveRef.current) return;
    const item = queueRef.current.shift();
    if (!item) return;
    const { sentence, voice } = item;
    if (!voice || (voice !== 'male' && voice !== 'female')) {
      // Strict: refuse to play a sentence without an explicit valid voice —
      // better to drop it than to play it in the wrong agent's voice.
      if (process.env.NODE_ENV === 'development') {
        // eslint-disable-next-line no-console
        console.warn('Sentence dropped: invalid/missing voice', voice);
      }
      if (queueRef.current.length > 0) playNextInQueue();
      return;
    }

    queueActiveRef.current = true;
    const msgIndex = queueMsgIndexRef.current;
    const token = getToken();
    const controller = new AbortController();
    queueAbortRef.current = controller;

    try {
      const response = await fetch(`${API_BASE}/tts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ text: sentence, voice }),
        signal: controller.signal,
      });
      if (!response.ok || cancelledRef.current) {
        queueActiveRef.current = false;
        return;
      }
      const blob = await response.blob();
      if (cancelledRef.current) return;
      const url = URL.createObjectURL(blob);
      const audio = audioElementRef?.current;
      if (!audio) {
        queueActiveRef.current = false;
        return;
      }
      clearAudioHandlers();
      revokeCurrentUrl();
      currentUrlRef.current = url;
      setPlayingTTS(msgIndex);

      audio.onended = () => {
        revokeCurrentUrl();
        queueActiveRef.current = false;
        if (queueRef.current.length > 0) {
          playNextInQueue();
        } else {
          setPlayingTTS(null);
        }
      };
      audio.onerror = () => {
        revokeCurrentUrl();
        queueActiveRef.current = false;
        if (queueRef.current.length > 0) {
          playNextInQueue();
        } else {
          setPlayingTTS(null);
        }
      };
      audio.src = url;
      try { await audio.play(); } catch { /* autoplay handled */ }
    } catch (err) {
      const benign = err?.name === 'AbortError';
      if (!benign && process.env.NODE_ENV === 'development') {
        // eslint-disable-next-line no-console
        console.warn('Sentence TTS error:', err?.message);
      }
      queueActiveRef.current = false;
      if (!cancelledRef.current && queueRef.current.length > 0) {
        playNextInQueue();
      }
    }
  }, [user?.selected_voice, audioElementRef, clearAudioHandlers, revokeCurrentUrl]);

  const resetTTSQueue = useCallback((msgIndex, voice) => {
    if (!ttsEnabled) return;
    stopTTS();
    cancelledRef.current = false;
    queueRef.current = [];
    queueActiveRef.current = false;
    queueMsgIndexRef.current = msgIndex;
    // Strict: only accept a real "male"/"female" — otherwise null so playNextInQueue
    // refuses to send (rather than risking the wrong agent's voice).
    queueVoiceRef.current = (voice === 'male' || voice === 'female') ? voice : null;
  }, [ttsEnabled, stopTTS]);

  const enqueueSentence = useCallback((sentence, voiceOverride) => {
    if (!ttsEnabled || !sentence || !sentence.trim()) return;
    // Per-sentence voice tagging — no shared mutable ref means voices can never
    // cross between Leon and Kylie even under rapid switches.
    const voice = (voiceOverride === 'male' || voiceOverride === 'female')
      ? voiceOverride
      : queueVoiceRef.current;
    if (voice !== 'male' && voice !== 'female') {
      if (process.env.NODE_ENV === 'development') {
        // eslint-disable-next-line no-console
        console.warn('enqueueSentence dropped: no valid voice tag', voiceOverride);
      }
      return;
    }
    queueRef.current.push({ sentence: sentence.trim(), voice });
    if (!queueActiveRef.current) playNextInQueue();
  }, [ttsEnabled, playNextInQueue]);

  // ---- Existing single-shot playTTS (greeting, manual replay) ----
  const playTTS = useCallback(async (text, msgIndex, voiceOverride) => {
    if (!ttsEnabled || !audioElementRef?.current) return;
    // Strict voice: never default to a different agent silently.
    const voice = (voiceOverride === 'male' || voiceOverride === 'female')
      ? voiceOverride
      : (user?.selected_voice === 'male' || user?.selected_voice === 'female')
        ? user.selected_voice
        : null;
    if (!voice) {
      if (process.env.NODE_ENV === 'development') {
        // eslint-disable-next-line no-console
        console.warn('playTTS dropped: no valid voice', voiceOverride, user?.selected_voice);
      }
      return;
    }
    stopTTS();
    cancelledRef.current = false;
    setPlayingTTS(msgIndex);

    const token = getToken();
    const controller = new AbortController();
    abortRef.current = controller;
    const audio = audioElementRef.current;

    const playViaBlob = async (resp) => {
      if (cancelledRef.current) return;
      let blob;
      try {
        blob = await resp.blob();
      } catch {
        if (!cancelledRef.current) setPlayingTTS(null);
        return;
      }
      if (cancelledRef.current) return;
      const audioUrl = URL.createObjectURL(blob);
      clearAudioHandlers();
      revokeCurrentUrl();
      currentUrlRef.current = audioUrl;

      audio.onended = () => {
        setPlayingTTS(null);
        revokeCurrentUrl();
      };
      audio.onerror = () => {
        setPlayingTTS(null);
        revokeCurrentUrl();
      };

      audio.src = audioUrl;
      try {
        await audio.play();
      } catch { /* autoplay handled by caller */ }
    };

    try {
      const response = await fetch(`${API_BASE}/tts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ text, voice }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body || cancelledRef.current) {
        if (!cancelledRef.current) setPlayingTTS(null);
        return;
      }

      const mime = 'audio/mpeg';
      const mseSupported =
        typeof window !== 'undefined' &&
        'MediaSource' in window &&
        window.MediaSource.isTypeSupported(mime);

      if (!mseSupported) {
        await playViaBlob(response);
        return;
      }

      // -------- MSE STREAMING path --------
      const mediaSource = new MediaSource();
      const url = URL.createObjectURL(mediaSource);
      currentUrlRef.current = url;

      clearAudioHandlers();
      audio.onended = () => {
        setPlayingTTS(null);
        revokeCurrentUrl();
      };
      audio.onerror = () => {
        setPlayingTTS(null);
        revokeCurrentUrl();
      };
      audio.src = url;

      await new Promise((resolve) => {
        mediaSource.addEventListener('sourceopen', resolve, { once: true });
      });

      if (cancelledRef.current) return;

      let sourceBuffer;
      try {
        sourceBuffer = mediaSource.addSourceBuffer(mime);
      } catch {
        clearAudioHandlers();
        try { audio.removeAttribute('src'); audio.load(); } catch { /* noop */ }
        revokeCurrentUrl();
        await playViaBlob(response);
        return;
      }

      const reader = response.body.getReader();
      const pendingChunks = [];
      let readerDone = false;
      let playbackStarted = false;

      const appendNext = () => {
        if (cancelledRef.current) return;
        if (sourceBuffer.updating) return;
        if (pendingChunks.length > 0) {
          try { sourceBuffer.appendBuffer(pendingChunks.shift()); } catch { /* noop */ }
        } else if (readerDone) {
          try { mediaSource.endOfStream(); } catch { /* noop */ }
        }
      };

      sourceBuffer.addEventListener('updateend', () => {
        if (!playbackStarted) {
          playbackStarted = true;
          audio.play().catch(() => { /* autoplay handled by caller */ });
        }
        appendNext();
      });

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (cancelledRef.current) {
            try { reader.cancel(); } catch { /* noop */ }
            return;
          }
          if (done) {
            readerDone = true;
            appendNext();
            break;
          }
          if (value && value.length) {
            pendingChunks.push(value);
            appendNext();
          }
        }
      } catch { /* stream aborted or read failed */ }
    } catch (err) {
      const benign = err?.name === 'AbortError'
        || err?.name === 'DataCloneError'
        || err?.code === 20
        || /Request object could not be cloned/i.test(err?.message || '');
      if (!benign && process.env.NODE_ENV === 'development') {
        // eslint-disable-next-line no-console
        console.warn('TTS playback error:', err?.name, err?.message);
      }
      if (!cancelledRef.current) setPlayingTTS(null);
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
    }
  }, [ttsEnabled, user?.selected_voice, stopTTS, audioElementRef, clearAudioHandlers, revokeCurrentUrl]);

  return { playTTS, stopTTS, playingTTS, ttsEnabled, toggleTTS, resetTTSQueue, enqueueSentence };
}
