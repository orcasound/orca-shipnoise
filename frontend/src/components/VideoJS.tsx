'use client';

import React, { useEffect, useRef } from 'react';
import videojs from 'video.js';

// Use ReturnType to avoid depending on internal typings
type Player = ReturnType<typeof videojs>;

export interface VideoJSOptions {
  autoplay?: boolean;
  controls?: boolean;
  responsive?: boolean;
  fluid?: boolean;
  preload?: string;
  sources?: Array<{ src: string; type: string }>;
  poster?: string | null | undefined;
  [key: string]: unknown;
}

interface VideoJSProps {
  options: VideoJSOptions;
  onReady?: (player: Player) => void;
}

/**
 * Thin React wrapper around a video.js player instance.
 * Creates the player on mount, disposes it on unmount.
 * Updates src/autoplay when options reference changes.
 */
const VideoJS: React.FC<VideoJSProps> = ({ options, onReady }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const playerRef = useRef<Player | null>(null);

  useEffect(() => {
    // Only initialise once
    if (playerRef.current) {
      // If already created, just update src / autoplay
      const player = playerRef.current;
      if (options.autoplay !== undefined) player.autoplay(options.autoplay as boolean);
      if (options.sources) player.src(options.sources);
      return;
    }

    const videoElement = document.createElement('video-js');
    videoElement.classList.add('vjs-big-play-centered');
    containerRef.current!.appendChild(videoElement);

    const player = videojs(videoElement, options, function () {
      onReady?.(player);
    });
    playerRef.current = player;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options, onReady]);

  // Dispose player on unmount
  useEffect(() => {
    return () => {
      const player = playerRef.current;
      if (player && !player.isDisposed()) {
        player.dispose();
        playerRef.current = null;
      }
    };
  }, []);

  return (
    <div data-vjs-player>
      <div ref={containerRef} />
    </div>
  );
};

export type { Player };
export default VideoJS;
