'use client';

import { useCallback, useMemo, useRef, useState } from 'react';
import Image from 'next/image';
import { Box, IconButton, Typography } from '@mui/material';
import VideoJS, { type Player, type VideoJSOptions } from '@/components/VideoJS';
import PlayButtonIcon from '@/assets/playbutton.svg';

interface LiveAudioPlayerProps {
  siteName: string;
  hlsUrl?: string;
  errored?: boolean;
}

const PLAY_BUTTON_SIZE = 40;

/**
 * Compact live-audio control bar. Mirrors DetectionsPlayer's pattern of
 * hiding the raw video.js element and driving playback through the
 * imperative player API -- there's no video content, just HLS audio, so a
 * full-size video.js UI would just be a wasted black rectangle.
 */
export default function LiveAudioPlayer({ siteName, hlsUrl, errored }: LiveAudioPlayerProps) {
  const playerRef = useRef<Player | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const videoJsOptions: VideoJSOptions = useMemo(
    () => ({
      autoplay: true,
      controls: false,
      responsive: false,
      fluid: false,
      preload: 'auto',
      sources: hlsUrl ? [{ src: hlsUrl, type: 'application/x-mpegURL' }] : [],
    }),
    [hlsUrl],
  );

  const handleReady = useCallback((player: Player) => {
    playerRef.current = player;
    player.on('playing', () => setIsPlaying(true));
    player.on('pause', () => setIsPlaying(false));
  }, []);

  const handlePlayPauseClick = useCallback(() => {
    const player = playerRef.current;
    if (!player) return;
    if (isPlaying) {
      player.pause();
    } else {
      player.play()?.catch(() => {
        // Playback blocked by the browser -- user can retry with another click.
      });
    }
  }, [isPlaying]);

  const statusLabel = errored
    ? 'Live audio unavailable'
    : hlsUrl
      ? `Live · ${siteName}`
      : 'Loading live audio…';

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 1 }}>
      {hlsUrl && (
        <Box display="none">
          <VideoJS options={videoJsOptions} onReady={handleReady} />
        </Box>
      )}

      <IconButton
        onClick={handlePlayPauseClick}
        disabled={!hlsUrl}
        sx={{ width: PLAY_BUTTON_SIZE, height: PLAY_BUTTON_SIZE, p: 0, borderRadius: '999px' }}
      >
        {isPlaying ? (
          <Box component="svg" width={PLAY_BUTTON_SIZE} height={PLAY_BUTTON_SIZE} viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="12" fill="#002447" />
            <path d="M8 6h3v12H8V6zm5 0h3v12h-3V6z" fill="white" />
          </Box>
        ) : (
          <Image
            src={PlayButtonIcon}
            alt="Play"
            width={PLAY_BUTTON_SIZE}
            height={PLAY_BUTTON_SIZE}
            style={{ width: '100%', height: '100%' }}
          />
        )}
      </IconButton>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box
          sx={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            bgcolor: errored ? '#6b7280' : '#dc2626',
          }}
        />
        <Typography sx={{ color: 'white', fontSize: 14 }}>{statusLabel}</Typography>
      </Box>
    </Box>
  );
}
