'use client';

import { useEffect, useState } from 'react';
import { Typography } from '@mui/material';
import type { SxProps, Theme } from '@mui/material';

const PACIFIC_DATE_FORMAT = new Intl.DateTimeFormat('en-US', {
  month: 'long',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'America/Los_Angeles',
});

const PACIFIC_TIME_FORMAT = new Intl.DateTimeFormat('en-US', {
  hour: 'numeric',
  minute: '2-digit',
  second: '2-digit',
  hour12: true,
  timeZone: 'America/Los_Angeles',
  timeZoneName: 'short',
});

interface LiveClockProps {
  sx?: SxProps<Theme>;
}

/** Live-updating current date/time in Pacific time, matching the format
 * used elsewhere in the app (see DetectionsPlayer). Renders nothing on the
 * server to avoid a hydration mismatch against the client's clock tick. */
export default function LiveClock({ sx }: LiveClockProps) {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    const intervalId = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(intervalId);
  }, []);

  if (!now) return null;

  return (
    <Typography variant="body2" sx={sx}>
      {PACIFIC_DATE_FORMAT.format(now)} | {PACIFIC_TIME_FORMAT.format(now)}
    </Typography>
  );
}
