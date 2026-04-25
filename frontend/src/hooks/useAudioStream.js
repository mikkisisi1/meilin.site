import { useState, useRef, useCallback } from 'react';
import { API_BASE, getToken } from '@/lib/apiClient';

/**
 * TTS playback hook with streaming via MediaSource Extensions where supported.
 * Audio starts playing as soon as the first MP3 chunk arrives from backend
 * (~300ms TTFB with Fish Audio `latency=balanced`).
 *
 * Fallback: if MediaSource or `audio/mpeg` is not supported (iOS Safari)
 * OR the MSE pipeline fails mid-stream → buffer into a Blob and play normally.
 */
export default function useAudioStream(user, audioElementRef) {
  const [playingTTS, setPlayingTTS] = useState(null);
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const cancelledRef = useRef(false);
  const abortRef = useRef(null);
  const currentUrlRef = useRef(null);

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

  const playTTS = useCallback(async (text, msgIndex, voiceOverride) => {
    if (!ttsEnabled || !audioElementRef?.current) return;
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
        body: JSON.stringify({ text, voice: voiceOverride || user?.selected_voice || 'female' }),
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
        // MSE rejected this MIME — tear down MSE, fall back to blob.
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
      } catch { /* stream aborted or read failed — onerror/onended will clean up */ }
    } catch (err) {
      // AbortError (user stopped) and DataCloneError (CRA HMR trying to
      // serialize Request/Response across dev postMessage) are expected and
      // do not affect audio playback — silence them.
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

  return { playTTS, stopTTS, playingTTS, ttsEnabled, toggleTTS };
}
