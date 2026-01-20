# Shipnoise Frontend

A Next.js frontend for browsing ship-noise audio clips. The UI supports site/date filtering, vessel search, and aggregates recent clips across multiple sites.

## Features

- Filter by site and date to view available clips
- Search by vessel name
- Query the FastAPI backend via `/clips/search` with multi-site search

## Tech Stack

- Next.js (App Router)
- React
- TypeScript
- Tailwind CSS

## Local Development

```bash
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

## Environment Variables

Set the backend API base URL in `.env.local`. This value is read in the browser (because of the `NEXT_PUBLIC_` prefix) and used to build `/clips/search` requests:

```bash
NEXT_PUBLIC_CLIPS_API_BASE_URL=
```

Set it to the base URL for your backend API. We have not deployed it yet, so leave it empty until the service is live, or point it to your local API during development.

The frontend calls `/clips/search` with `shipname`, `start_date`, `end_date`, `sites`, and `limit_per_site`, and uses the FastAPI JSON response (including `audio_urls` pointing to S3-hosted audio). `shipname` is populated from the vessel name input (or left blank for all vessels).

Example (replace with your backend base URL):

```bash
curl 'https://your-backend-host/clips/search?shipname=&start_date=2025-11-01&end_date=2025-11-08&sites=Bush_Point&limit_per_site=5'
```

## Scripts

```bash
npm run dev     # local dev server
npm run build   # production build
npm run start   # start production server
npm run lint    # lint
```

## Project Structure

```
src/
  app/          # routes and pages
  components/   # reusable components
  lib/          # helpers/utilities
  types/        # type definitions
  assets/       # static assets
public/         # public static files
```
