'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import Image from 'next/image';
import { Box, IconButton, Stack, Typography } from '@mui/material';
import muxjs from 'mux.js';
import PlayButtonIcon from '@/assets/playbutton.svg';
import { generateWaveform } from '@/lib/waveform';

interface InlineWavePlayerProps {
  audioUrls?: string[];
  src?: string;
  date?: string;
  time?: string;
  timestamp?: string | null;
  onPlayStart?: () => void;
}

const DEFAULT_AUDIO_SRC =
  'https://incompetech.com/music/royalty-free/mp3-royaltyfree/Easy%20Lemon%2030%20second.mp3';

const WAVE_BAR_COUNT = 120;
const PLAY_BUTTON_SIZE = 74;

type TransmuxSegment = {
  initSegment: Uint8Array;
  data: Uint8Array;
};

const InlineWavePlayer: React.FC<InlineWavePlayerProps> = ({ 
  audioUrls, 
  src, 
  date, 
  time, 
  timestamp, 
  onPlayStart 
}) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  
  // Playback State
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [segmentDurations, setSegmentDurations] = useState<number[]>([]);
  
  // Segment State
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState(0);
  
  // Transcoding State
  const [playableSrc, setPlayableSrc] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);

  // Normalize playlist using backend-provided URLs; do not duplicate segments.
  const playlist = useMemo(() => {
    const filtered = (audioUrls ?? []).filter((url) => typeof url === 'string' && url.trim().length > 0);
    if (filtered.length > 0) return filtered;
    if (src?.trim()) return [src.trim()];
    return [DEFAULT_AUDIO_SRC];
  }, [audioUrls, src]);

  // Determine the raw source URL
  const rawAudioSrc = useMemo(() => {
    if (playlist.length > 0) {
      const safeIndex = Math.min(currentSegmentIndex, playlist.length - 1);
      return playlist[safeIndex];
    }
    return DEFAULT_AUDIO_SRC;
  }, [playlist, currentSegmentIndex]);

  // Generate waveform
  const waveformSeed = (playlist[0] || DEFAULT_AUDIO_SRC).length;
  const [waveBars] = useState<number[]>(() =>
    generateWaveform(WAVE_BAR_COUNT, {
      fadeStartRatio: 0.7,
      seed: waveformSeed,
    }),
  );

  // Reset playback when playlist changes
  useEffect(() => {
    setCurrentSegmentIndex(0);
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    setPlayableSrc('');
    setSegmentDurations(Array(playlist.length).fill(0));
  }, [playlist]);

  // Core Logic: Download .ts file and transmux to MP4
  useEffect(() => {
    let active = true;
    const audio = audioRef.current;

    const loadAndTransmux = async () => {
      if (!rawAudioSrc) return;

      // Handle simple MP3s without transmuxing
      if (rawAudioSrc.endsWith('.mp3')) {
        setPlayableSrc(rawAudioSrc);
        return;
      }

      setIsLoading(true);
      try {
        const response = await fetch(rawAudioSrc);
        const buffer = await response.arrayBuffer();
        if (!active) return;

        const transmuxer = new muxjs.mp4.Transmuxer();
        
        transmuxer.on('data', (segment: TransmuxSegment) => {
          if (!active) return;
          
          const data = new Uint8Array(segment.initSegment.byteLength + segment.data.byteLength);
          data.set(segment.initSegment, 0);
          data.set(segment.data, segment.initSegment.byteLength);

          const blob = new Blob([data], { type: 'audio/mp4' });
          const blobUrl = URL.createObjectURL(blob);
          
          setPlayableSrc(blobUrl);
          setIsLoading(false);
        });

        transmuxer.push(new Uint8Array(buffer));
        transmuxer.flush();

      } catch (err) {
        console.error("Transmux error:", err);
        if (active) setIsLoading(false);
      }
    };

    loadAndTransmux();

    return () => {
      active = false;
      if (playableSrc.startsWith('blob:')) {
        URL.revokeObjectURL(playableSrc);
      }
    };
  }, [rawAudioSrc]);

  // Monitor playableSrc and handle playback
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !playableSrc) return;

    // Only set src if it changed to avoid reloading same blob
    if (audio.src !== playableSrc) {
        audio.src = playableSrc;
        audio.load();
    }

    if (isPlaying && currentSegmentIndex > 0) {
       audio.play().catch(e => console.log('Autoplay blocked:', e));
    }

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime);
    const handleLoaded = () => {
      setDuration(audio.duration);
      setSegmentDurations((prev) => {
        const next = [...prev];
        next[currentSegmentIndex] = audio.duration || 0;
        return next;
      });
    };
    
    const handleEnded = () => {
      if (playlist && currentSegmentIndex < playlist.length - 1) {
        setCurrentSegmentIndex((prev) => prev + 1);
      } else {
        setIsPlaying(false);
        setCurrentSegmentIndex(0);
      }
    };

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('loadedmetadata', handleLoaded);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('loadedmetadata', handleLoaded);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [playableSrc, currentSegmentIndex, playlist]); 

  // Format Date Time
  const formattedDateTime = useMemo(() => {
    const pacificFormatter = new Intl.DateTimeFormat('en-US', {
      month: 'long', day: 'numeric', year: 'numeric', timeZone: 'America/Los_Angeles',
    });
    const pacificTimeFormatter = new Intl.DateTimeFormat('en-US', {
      hour: 'numeric', minute: '2-digit', hour12: true, timeZone: 'America/Los_Angeles', timeZoneName: 'short',
    });

    if (timestamp) {
      const parsed = new Date(timestamp);
      if (!Number.isNaN(parsed.getTime())) {
        return `${pacificFormatter.format(parsed)} | ${pacificTimeFormatter.format(parsed)}`;
      }
    }
    if (!date && !time) return '';
    return `${date} | ${time}`; 
  }, [date, time, timestamp]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio || isLoading) return; 

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      audio.play().then(() => {
        setIsPlaying(true);
        onPlayStart?.();
      }).catch((err) => {
        console.error("Play failed:", err);
        setIsPlaying(false);
      });
    }
  };

  const setProgress = (event: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    if (!audio || !duration) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const percent = (event.clientX - rect.left) / rect.width;
    audio.currentTime = percent * duration;
  };

  const formatTime = (sec: number) => {
    if (!Number.isFinite(sec)) return '0:00';
    const minutes = Math.floor(sec / 60);
    const seconds = Math.floor(sec % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const knownDurations = segmentDurations.filter((d) => d > 0);
  const avgDuration = knownDurations.length
    ? knownDurations.reduce((a, b) => a + b, 0) / knownDurations.length
    : 10;
  const estimatedTotalDuration =
    segmentDurations.reduce((sum, d) => sum + (d || 0), 0) +
    segmentDurations.filter((d) => d === 0).length * avgDuration;

  const elapsedBeforeCurrent = segmentDurations
    .slice(0, currentSegmentIndex)
    .reduce((sum, d) => sum + (d || avgDuration), 0);

  const overallCurrentTime = elapsedBeforeCurrent + currentTime;

  const activeBarIndex = estimatedTotalDuration
    ? Math.floor((overallCurrentTime / estimatedTotalDuration) * waveBars.length)
    : -1;

  return (
    <Box sx={{ position: 'relative', width: '100%' }}>
      <Stack
        direction={{ xs: 'column', md: 'row' }}
        spacing={2}
        alignItems={{ md: 'flex-start' }}
        sx={{ width: '100%' }}
      >
        <Stack alignItems="center" spacing={0.5} sx={{ alignSelf: { xs: 'flex-start', md: 'auto' } }}>
          <IconButton
            onClick={togglePlay}
            disabled={isLoading}
            sx={{
              width: { xs: 64, md: 74 },
              height: { xs: 64, md: 74 },
              borderRadius: '999px',
              opacity: isLoading ? 0.5 : 1,
              cursor: isLoading ? 'wait' : 'pointer',
              p: 0,
            }}
          >
            {isPlaying ? (
              <Box
                component="svg"
                width={PLAY_BUTTON_SIZE}
                height={PLAY_BUTTON_SIZE}
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                sx={{ width: { xs: 64, md: 74 }, height: { xs: 64, md: 74 } }}
              >
                <circle cx="12" cy="12" r="12" fill="#013C74" />
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
          <Typography
            sx={{
              pointerEvents: 'none',
              fontSize: { xs: '14px', md: '16px' },
              fontWeight: 400,
              color: '#4C4C51',
            }}
          >
            {isLoading ? 'Loading' : isPlaying ? 'Pause' : 'Play'}
          </Typography>
        </Stack>

        <Box
          sx={{
            width: '100%',
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            gap: 1.5,
            ml: { md: '28px' },
            mt: { md: '22px' },
            maxWidth: { md: 1030 },
          }}
        >
        {formattedDateTime && (
          <Typography
            sx={{
              fontSize: { xs: '14px', md: '16px' },
              color: '#4b5563',
            }}
          >
            {formattedDateTime}
          </Typography>
        )}

        <Box
          onClick={setProgress}
          sx={{
            display: 'flex',
              alignItems: 'flex-end',
              justifyContent: 'space-between',
              width: '100%',
              height: { xs: 48, md: 52 },
              cursor: 'pointer',
              overflow: 'hidden',
              borderRadius: { xs: '6px', md: 0 },
              bgcolor: '#E5E7EB',
              px: { xs: 1, md: 0 },
            }}
          >
            {waveBars.map((height, idx) => (
              <Box
                key={idx}
                sx={{
                  width: 4,
                  borderRadius: '999px',
                  bgcolor: idx <= activeBarIndex ? '#013C74' : '#d1d5db',
                  height: `${height}px`,
                  minHeight: '6px',
                }}
              />
            ))}
          </Box>
          <Stack direction="row" justifyContent="space-between" sx={{ mt: 1 }}>
            <Typography sx={{ fontSize: '12px', color: '#6b7280' }}>
              {formatTime(overallCurrentTime)}
            </Typography>
            <Typography sx={{ fontSize: '12px', color: '#6b7280' }}>
              {isLoading ? 'Loading...' : formatTime(estimatedTotalDuration)}
            </Typography>
          </Stack>
        </Box>
      </Stack>

      <audio ref={audioRef} preload="metadata" />
    </Box>
  );
};

export default InlineWavePlayer;
