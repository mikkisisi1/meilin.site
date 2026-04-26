import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Play, Pause, Radio } from 'lucide-react';

const YOUTUBE_MIX_ID = 'pjXs6XPtuKU';

export default function MiroRadio() {
  const { t } = useLanguage();
  const navigate = useNavigate();
  const [playing, setPlaying] = useState(false);
  const [playerReady, setPlayerReady] = useState(false);
  const playerRef = useRef(null);

  const loadYouTubeAPI = useCallback(() => {
    if (window.YT && window.YT.Player) {
      initPlayer();
      return;
    }
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    document.head.appendChild(tag);
    window.onYouTubeIframeAPIReady = initPlayer;
  }, []);

  const initPlayer = () => {
    if (playerRef.current) return;
    playerRef.current = new window.YT.Player('yt-player', {
      height: '0',
      width: '0',
      videoId: YOUTUBE_MIX_ID,
      playerVars: { autoplay: 0, loop: 1, playlist: YOUTUBE_MIX_ID },
      events: {
        onReady: () => setPlayerReady(true),
        onStateChange: (e) => {
          if (e.data === window.YT.PlayerState.ENDED) {
            playerRef.current?.playVideo();
          }
        },
      },
    });
  };

  useEffect(() => { loadYouTubeAPI(); }, [loadYouTubeAPI]);

  const togglePlay = () => {
    if (!playerRef.current) return;
    if (playing) {
      playerRef.current.pauseVideo();
    } else {
      playerRef.current.playVideo();
    }
    setPlaying(!playing);
  };

  return (
    <div className="radio-page" data-testid="radio-page">
      <header className="page-header">
        <button data-testid="radio-back-btn" onClick={() => navigate(-1)} className="header-back-btn">
          <ArrowLeft size={20} />
        </button>
        <h1>{t('radio')}</h1>
      </header>

      <div className="radio-content">
        <div className="radio-visual">
          <div className={`radio-disc ${playing ? 'radio-disc-spinning' : ''}`}>
            <Radio size={48} />
          </div>
        </div>

        <h2 className="radio-title">SlimLight Radio</h2>
        <p className="radio-desc">{t('musicDesc')}</p>

        <button
          data-testid="radio-toggle-btn"
          onClick={togglePlay}
          disabled={!playerReady}
          className={`radio-play-btn ${playing ? 'radio-playing' : ''}`}
        >
          {playing ? <Pause size={24} /> : <Play size={24} />}
          <span>{playing ? t('playing') : 'Play'}</span>
        </button>

        <p className="radio-status" data-testid="radio-status">
          {playing ? t('playing') : t('paused')}
        </p>
      </div>

      <div id="yt-player" style={{ position: 'absolute', left: '-9999px' }} />
    </div>
  );
}
