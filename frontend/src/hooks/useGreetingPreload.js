import { useEffect, useRef } from 'react';
import { getGreeting } from '@/contexts/translations-extra';
import { API_BASE } from '@/lib/apiClient';

const FALLBACK_GREETINGS = {
  male: "Hi, I'm Leon — I'm here to support you.\nHow are you feeling today?",
  female: "Hi, I'm Kylie — I'm here to support you.\nHow are you feeling today?",
};

export const getLangGreeting = (lang, voice) =>
  getGreeting(lang, voice) || FALLBACK_GREETINGS[voice];

/**
 * Pre-fetches the male + female greeting MP3s as soon as the user lands on the
 * chat page. The first one to be played hits a cached blob URL, which removes
 * the perceptible TTS round-trip when the user picks an agent.
 *
 * Returns a ref whose .current is `{ male: string|null, female: string|null }`
 * — caller can read the URL and feed it to <audio>.src directly.
 *
 * Cache is invalidated whenever `lang` changes (different greeting text) or
 * once the user has chosen a voice (no need to keep both around).
 */
export default function useGreetingPreload({ voiceChosen, lang }) {
  const greetingCacheRef = useRef({ male: null, female: null });

  useEffect(() => {
    if (voiceChosen) return undefined;
    let cancelled = false;

    const preloadGreeting = async (voice) => {
      try {
        const text = getLangGreeting(lang, voice);
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
        if (process.env.NODE_ENV === 'development') {
          // eslint-disable-next-line no-console
          console.error('TTS greeting cache miss:', err.message);
        }
      }
    };

    preloadGreeting('male');
    preloadGreeting('female');

    return () => {
      cancelled = true;
      greetingCacheRef.current = { male: null, female: null };
    };
  }, [voiceChosen, lang]);

  return greetingCacheRef;
}
