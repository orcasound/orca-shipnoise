# Shipnoise Frontend

Next.js UI for searching vessels, aggregating multi-site clips across ~30 days, inline playback, and viewing reported issues.

## Quick Start

```bash
npm install
npm run dev
# open http://localhost:3000
```

Build and production serve:

```bash
npm run build
npm start
```

Environment (`.env.local`):

```bash
CLIPS_API_BASE_URL=https://<your-api-host>      # required: FastAPI base URL
# optional if upstream returns only an S3 key
CLIPS_AUDIO_BASE_URL=https://your-audio-bucket-or-cloudfront-domain
```

## Data Pipeline

1) **Vessel autocomplete**: `SelectionPanel` calls `/api/vessels/search`, which proxies to `${CLIPS_API_BASE_URL}/vessels/search` and returns candidate names.  
2) **Clip aggregation**: Search triggers `/api/clips/search`:  
   - Primary: `${CLIPS_API_BASE_URL}/clips/search` for multi-site aggregated results.  
   - Fallback: per-day, per-site fetch via `/api/clips` (proxy to `${CLIPS_API_BASE_URL}/clips`) to collect up to 5 matches per site over the last 30 days.  
3) **Playback**: UI passes `presigned_url`/`record_url` to `InlineWavePlayer`; falls back to a sample audio if missing.  
4) **Issue dashboard**: `/report` calls `/api/issues`, which forwards to a Google Apps Script endpoint and renders sorted submissions.

## Files and Roles

- `src/app/page.tsx`: Home entry; renders `Banner` and `SelectionPanel`.  
- `src/app/layout.tsx`, `src/app/globals.css`: App shell and global styles.  
- `src/components/Banner.tsx`: Black header with logo, improvement link, and Tally feedback modal.  
- `src/components/SelectionPanel.tsx`: Core search panel handling input, autocomplete, multi-site querying, and status.  
- `src/components/AvailableRecordings.tsx`: Groups results by site with expand/collapse and Mailchimp script load.  
- `src/components/InlineWavePlayer.tsx`: Inline audio player with faux waveform and seek.  
- `src/lib/waveform.ts`: Generates pseudo-random waveform heights.  
- `src/app/api/clips/route.ts`: Same-origin proxy for `site+date` queries to upstream `/clips`.  
- `src/app/api/clips/search/route.ts`: Aggregated or fallback multi-site search logic.  
- `src/app/api/vessels/search/route.ts`: Vessel/MMSI autocomplete proxy.  
- `src/app/api/issues/route.ts`: Fetches issue list from Google Apps Script.  
- `src/app/report/page.tsx`: Issue dashboard with detail modal.  
- `next.config.ts`, `tsconfig.json`, `eslint.config.mjs`, `postcss.config.mjs`: Build, type-check, and styling configs.  
- `public/`: Static assets; `src/assets/` images and SVGs for components.

## Usage Notes

- **Search**: Type vessel name or MMSI, pick an autocomplete option, click Search; results group by site and can expand to play.  
- **Playback**: Browsers may require a first click to start audio; the waveform bar supports seeking.  
- **Feedback**: Header button opens the Tally form; `/report` shows collected submissions.

## Scripts

- `npm run dev`: Local development.  
- `npm run build`: Production build.  
- `npm start`: Serve the production build.  
- `npm run lint`: ESLint check.
