'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import Image from 'next/image';
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
    <div className="relative w-full">
      <div className="flex w-full flex-col gap-4 md:flex-row md:items-start md:gap-4">
        <button
          onClick={togglePlay}
          disabled={isLoading}
          className={`flex h-[64px] w-[64px] shrink-0 items-center justify-center self-start rounded-full md:h-[74px] md:w-[74px] ${isLoading ? 'opacity-50 cursor-wait' : 'cursor-pointer'}`}
        >
          {isPlaying ? (
            <svg
              width={PLAY_BUTTON_SIZE}
              height={PLAY_BUTTON_SIZE}
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="h-[64px] w-[64px] md:h-[74px] md:w-[74px]"
            >
              <circle cx="12" cy="12" r="12" fill="#013C74" />
              <path d="M8 6h3v12H8V6zm5 0h3v12h-3V6z" fill="white" />
            </svg>
          ) : (
            <Image
              src={PlayButtonIcon}
              alt="Play"
              width={PLAY_BUTTON_SIZE}
              height={PLAY_BUTTON_SIZE}
              className="h-[64px] w-[64px] md:h-[74px] md:w-[74px]"
            />
          )}
        </button>

        <div className="flex w-full flex-1 flex-col gap-3 md:ml-[28px] md:mt-[22px] md:max-w-[1030px]">
          <div
            className="flex h-12 w-full cursor-pointer items-end justify-between overflow-hidden rounded-md bg-[#E5E7EB] px-2 md:h-[52px] md:rounded-none md:px-0"
            onClick={setProgress}
          >
            {waveBars.map((height, idx) => (
              <div
                key={idx}
                className={`w-1 rounded-full ${idx <= activeBarIndex ? 'bg-[#013C74]' : 'bg-gray-300'}`}
                style={{ height: `${height}px`, minHeight: '6px' }}
              />
            ))}
          </div>
          <div className="mt-2 flex justify-between text-xs text-gray-500">
            <span>{formatTime(overallCurrentTime)}</span>
            <span>{isLoading ? 'Loading...' : formatTime(estimatedTotalDuration)}</span>
          </div>
        </div>
      </div>

      <span className="pointer-events-none mt-2 block text-sm font-normal text-[#4C4C51] md:absolute md:left-[20px] md:top-[81px] md:mt-0 md:text-[16px]">
        {isLoading ? 'Loading' : isPlaying ? 'Pause' : 'Play'}
      </span>

      {formattedDateTime && (
        <div className="mt-1 text-sm text-gray-600 md:absolute md:left-[118px] md:-top-[7px] md:mt-0 md:text-[16px]">
          {formattedDateTime}
        </div>
      )}

      <audio ref={audioRef} preload="metadata" />
    </div>
  );
};

export default InlineWavePlayer;
