type WaveformOptions = {
  fadeStartRatio?: number;
  minHeight?: number;
  maxHeight?: number;
  minFadeMultiplier?: number;
  seed?: number;
};

const DEFAULT_MIN_HEIGHT = 10;
const DEFAULT_MAX_HEIGHT = 50;
const DEFAULT_MIN_FADE_MULTIPLIER = 0.1;
const DEFAULT_SEED = 1;

const pseudoRandom = (seed: number) => {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
};

export function generateWaveform(
  count: number,
  {
    fadeStartRatio,
    minHeight = DEFAULT_MIN_HEIGHT,
    maxHeight = DEFAULT_MAX_HEIGHT,
    minFadeMultiplier = DEFAULT_MIN_FADE_MULTIPLIER,
    seed = DEFAULT_SEED,
  }: WaveformOptions = {},
): number[] {
  const fadeStartIndex =
    fadeStartRatio !== undefined
      ? Math.floor(count * fadeStartRatio)
      : Number.POSITIVE_INFINITY;
  const heightRange = maxHeight - minHeight;

  return Array.from({ length: count }, (_, idx) => {
    const base =
      pseudoRandom(seed + idx + 1) * heightRange + minHeight;
    if (idx <= fadeStartIndex) {
      return base;
    }

    const fadeProgress = (idx - fadeStartIndex) / Math.max(1, count - fadeStartIndex);
    const fadeMultiplier = Math.max(minFadeMultiplier, 1 - fadeProgress);
    return base * fadeMultiplier;
  });
}

