'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { notFound, useParams } from 'next/navigation';
import { Box, Typography } from '@mui/material';
import LiveAudioPlayer from '@/components/LiveAudioPlayer';
import { useAisSite } from '@/hooks/useShipnoiseApi';
import { useLiveStreamUrl } from '@/hooks/useLiveStream';
import { SITES_BY_SLUG } from '@/lib/sites';

const SiteMap = dynamic(() => import('@/components/SiteMap'), {
  ssr: false,
});

export default function SiteFullscreenPage() {
  const { slug } = useParams<{ slug: string }>();
  const site = SITES_BY_SLUG[slug];

  const { data: aisData } = useAisSite(slug);
  const vessels = aisData?.vessels ?? [];

  const { data: hlsUrl, isError: streamErrored } = useLiveStreamUrl(site?.bucket, site?.nodeName);

  if (!site) {
    notFound();
  }

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Box
        sx={{
          bgcolor: 'black',
          color: 'white',
          px: 2,
          py: 1.5,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 1,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Link href="/ais-maps" style={{ color: 'white', textDecoration: 'none' }}>
            &larr; All sites
          </Link>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {site.name}
          </Typography>
        </Box>
        <Typography variant="body2" sx={{ color: '#9ca3af' }}>
          {vessels.length} vessel{vessels.length === 1 ? '' : 's'} nearby
        </Typography>
      </Box>

      <Box sx={{ flex: 1, minHeight: 0 }}>
        <SiteMap site={site} vessels={vessels} />
      </Box>

      <Box sx={{ bgcolor: '#111827', px: 2 }}>
        <LiveAudioPlayer siteName={site.name} hlsUrl={hlsUrl} errored={streamErrored} />
      </Box>
    </Box>
  );
}
