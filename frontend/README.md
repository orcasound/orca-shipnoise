This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Shipnoise Clips API

The app now proxies your EC2 database-backed API so the UI can stay on the same origin. Configure the server-to-server hop via environment variables in `.env.local`:

```bash
CLIPS_API_BASE_URL=http://18.191.247.109:8000
```

`/api/clips` accepts the same query parameters as the EC2 FastAPI service (`site`, `date`, optional `limit`) and forwards the FastAPI JSON (including `audio_urls` with fully qualified TS segment URLs). Use any of the four site codes (`Bush_Point`, `Orcasound_Lab`, `Port_Townsend`, `Sunset_Bay`):

```bash
curl 'http://localhost:3000/api/clips?site=Bush_Point&date=2025-11-08'
```

In the selection panel users type a vessel/MMSI (or leave it blank) and hit Search; the app automatically queries all four sites for the most recent UTC day plus the previous 4 days, so if a vessel appears multiple times across the window you’ll see every clip stacked in the existing UI. If no clips are found across that window you’ll see a warning instead.
