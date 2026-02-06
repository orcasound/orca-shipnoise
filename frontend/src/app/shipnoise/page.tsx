'use client';

import { Box, Container } from '@mui/material';
import Banner from '@/components/Banner';
import SelectionPanel from '@/components/SelectionPanel';

export default function ShipnoisePage() {
  return (
    <Box sx={{ minHeight: '100vh' }}>
      <Banner />
      <Container
        maxWidth={false}
        sx={{
          maxWidth: '90rem',
          px: { xs: 2, sm: 3 },
          pt: { xs: 1, lg: 1.5 },
        }}
      >
        <SelectionPanel />
      </Container>
    </Box>
  );
}
