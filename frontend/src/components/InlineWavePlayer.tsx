'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import Image from 'next/image';
import PlayButtonIcon from '@/assets/playbutton.svg';
import { generateWaveform } from '@/lib/waveform';

interface InlineWavePlayerProps {
  src: string;
  date?: string;
  time?: string;
  timestamp?: string | null;
  onPlayStart?: () => void;
}

const DEFAULT_AUDIO_SRC =
  'https://incompetech.com/music/royalty-free/mp3-royaltyfree/Easy%20Lemon%2030%20second.mp3';

const WAVE_BAR_COUNT = 120;

const PLAY_BUTTON_SIZE = 74;

const InlineWavePlayer: React.FC<InlineWavePlayerProps> = ({ src, date, time, timestamp, onPlayStart }) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const audioSrc = src?.trim() ? src : DEFAULT_AUDIO_SRC;
  const [waveBars] = useState<number[]>(() =>
    generateWaveform(WAVE_BAR_COUNT, {
      fadeStartRatio: 0.7,
      seed: audioSrc.length,
    }),
  );

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.src = audioSrc;
    audio.load();

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime);
    const handleLoaded = () => setDuration(audio.duration);
    const handleEnded = () => setIsPlaying(false);

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('loadedmetadata', handleLoaded);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('loadedmetadata', handleLoaded);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [audioSrc]);

  const formattedDateTime = useMemo(() => {
    const pacificFormatter = new Intl.DateTimeFormat('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      timeZone: 'America/Los_Angeles',
    });

    const pacificTimeFormatter = new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      timeZone: 'America/Los_Angeles',
      timeZoneName: 'short',
    });

    if (timestamp) {
      const parsed = new Date(timestamp);
      if (!Number.isNaN(parsed.getTime())) {
        const prettyDate = pacificFormatter.format(parsed);
        const prettyTime = pacificTimeFormatter.format(parsed);
        return `${prettyDate} | ${prettyTime}`;
      }
    }

    if (!date && !time) return '';

    const formatDate = (value?: string) => {
      if (!value) return '';
      const parsed = new Date(`${value}T00:00:00Z`);
      if (Number.isNaN(parsed.getTime())) return value;
      return pacificFormatter.format(parsed);
    };

    const formatTime = (value?: string) => {
      if (!value) return '';
      const parsed = new Date(`1970-01-01T${value.replace(/\s+.*/, '') || '00:00'}Z`);
      if (Number.isNaN(parsed.getTime())) return value;
      return pacificTimeFormatter.format(parsed);
    };

    const prettyDate = formatDate(date);
    const prettyTime = formatTime(time);

    return [prettyDate, prettyTime].filter(Boolean).join(' | ');
  }, [date, time, timestamp]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      audio.play().then(() => {
        setIsPlaying(true);
        onPlayStart?.();
      }).catch(() => {
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

  const activeBarIndex = duration
    ? Math.floor((currentTime / duration) * waveBars.length)
    : -1;

  return (
    <div className="relative w-full">
      <div className="flex w-full flex-col gap-4 md:flex-row md:items-start md:gap-4">
        <button
          onClick={togglePlay}
          className="flex h-[64px] w-[64px] shrink-0 items-center justify-center self-start rounded-full cursor-pointer md:h-[74px] md:w-[74px]"
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
            <span>{formatTime(0)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>
      </div>

      <span className="pointer-events-none mt-2 block text-sm font-normal text-[#4C4C51] md:absolute md:left-[20px] md:top-[81px] md:mt-0 md:text-[16px]">
        {isPlaying ? 'Pause' : 'Play'}
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
