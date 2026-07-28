'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { Box, Container, Grid, Paper, Typography } from '@mui/material';
import Banner from '@/components/Banner';
import LiveClock from '@/components/LiveClock';
import { useAisSite } from '@/hooks/useShipnoiseApi';
import { SITES, type Site } from '@/lib/sites';

const SiteMap = dynamic(() => import('@/components/SiteMap'), {
  ssr: false,
});

function formatUpdatedLabel(updatedAt: string | null): string {
  if (!updatedAt) return 'Waiting for first update…';
  const ageSec = Math.max(0, (Date.now() - new Date(updatedAt).getTime()) / 1000);
  if (ageSec < 60) return 'Updated just now';
  const ageMin = Math.round(ageSec / 60);
  return `Updated ${ageMin} min ago`;
}

function SiteTile({ site }: { site: Site }) {
  const { data, isLoading } = useAisSite(site.slug);
  const vessels = data?.vessels ?? [];

  return (
    <Link href={`/ais-maps/${site.slug}`} style={{ textDecoration: 'none', color: 'inherit' }}>
      <Paper
        variant="outlined"
        sx={{
          overflow: 'hidden',
          borderRadius: 2,
          cursor: 'pointer',
          transition: 'box-shadow 0.15s ease',
          '&:hover': { boxShadow: 3 },
        }}
      >
        <Box sx={{ aspectRatio: '4 / 3', bgcolor: '#e8edf1' }}>
          {isLoading ? (
            <Box
              sx={{
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Typography variant="body2" sx={{ color: '#6b7c85' }}>
                Loading map…
              </Typography>
            </Box>
          ) : (
            <SiteMap site={site} vessels={vessels} interactive={false} />
          )}
        </Box>
        <Box sx={{ p: 1.5 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            {site.name}
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            {vessels.length} vessel{vessels.length === 1 ? '' : 's'} nearby &middot;{' '}
            {formatUpdatedLabel(data?.updated_at ?? null)}
          </Typography>
        </Box>
      </Paper>
    </Link>
  );
}

export default function AisMapsPage() {
  return (
    <Box sx={{ minHeight: '100vh' }}>
      <Banner />
      <Container
        maxWidth={false}
        sx={{
          maxWidth: '90rem',
          px: { xs: 2, sm: 3 },
          py: { xs: 2, lg: 3 },
        }}
      >
        <Box sx={{ mb: 2 }}>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            Nearby Ship Traffic
          </Typography>
          <LiveClock sx={{ color: 'text.secondary', mt: 0.5 }} />
        </Box>
        <Grid container spacing={2}>
          {SITES.map((site) => (
            <Grid key={site.slug} size={{ xs: 12, sm: 6, md: 4 }}>
              <SiteTile site={site} />
            </Grid>
          ))}
        </Grid>
      </Container>
    </Box>
  );
}
