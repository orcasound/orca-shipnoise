'use client';

import { Box, Container, Grid, Paper, Typography } from '@mui/material';
import Banner from '@/components/Banner';

type Site = {
  slug: string;
  name: string;
  lat: number;
  lon: number;
};

// Source: https://live.orcasound.net/api/json/feeds (visible: true)
// Ordered north to south so the grid reads geographically, top to bottom.
const SITES: Site[] = [
  { slug: 'orcasound-lab', name: 'Orcasound Lab', lat: 48.5583, lon: -123.1736 },
  { slug: 'andrews-bay', name: 'Andrews Bay', lat: 48.5467, lon: -123.1664 },
  { slug: 'north-sjc', name: 'North San Juan Channel', lat: 48.5913, lon: -123.0588 },
  { slug: 'port-townsend', name: 'Port Townsend', lat: 48.1357, lon: -122.7606 },
  { slug: 'bush-point', name: 'Bush Point', lat: 48.0337, lon: -122.604 },
  { slug: 'sunset-bay', name: 'Sunset Bay', lat: 47.865, lon: -122.3339 },
  { slug: 'mast-center', name: 'MaST Center Aquarium', lat: 47.3492, lon: -122.3251 },
];

function SiteMapPlaceholder({ site }: { site: Site }) {
  return (
    <Paper
      variant="outlined"
      sx={{
        overflow: 'hidden',
        borderRadius: 2,
      }}
    >
      <Box
        sx={{
          aspectRatio: '4 / 3',
          bgcolor: '#e8edf1',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Typography variant="body2" sx={{ color: '#6b7c85' }}>
          AIS map coming soon
        </Typography>
      </Box>
      <Box sx={{ p: 1.5 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
          {site.name}
        </Typography>
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          {site.lat.toFixed(4)}, {site.lon.toFixed(4)}
        </Typography>
      </Box>
    </Paper>
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
        <Typography variant="h5" sx={{ fontWeight: 600, mb: 2 }}>
          Nearby Ship Traffic
        </Typography>
        <Grid container spacing={2}>
          {SITES.map((site) => (
            <Grid key={site.slug} size={{ xs: 12, sm: 6, md: 4 }}>
              <SiteMapPlaceholder site={site} />
            </Grid>
          ))}
        </Grid>
      </Container>
    </Box>
  );
}
