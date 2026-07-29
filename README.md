# shipnoise.net

A web application for visualizing and listening to underwater ship noise recorded by [Orcasound](https://orcasound.net) hydrophones in the Salish Sea. The goal is to help researchers and the public understand — and eventually reduce — noise pollution affecting the endangered Southern Resident killer whales.

---

## 1. What this project does, and how it serves web pages

The site has two live features, both served from the same Next.js frontend:

- **`/shipnoise`** — search historical "detections": moments when a ship's closest point of approach (CPA) to a hydrophone was captured, matched against Orcasound's audio archive, with a player that seeks straight to that moment.
- **`/ais-maps`** — a live map, per hydrophone site, of ships currently nearby (position, speed, heading), refreshed continuously.

Neither page stores or re-hosts audio. Everything the user hears streams directly from Orcasound's public HLS/S3 infrastructure — the app's job is to figure out *which* segment is worth listening to, not to host it.

```
AISstream (live AIS feed)  ─┐                                 AISHub (on-demand AIS lookup)
                            ├→ scripts/ pipeline (fly.io) →┐        │
AWS S3 (Orcasound HLS audio)┘        ↓                     │        ↓
                              SQLite `records` table  ──→ FastAPI backend ←── in-memory AIS cache
                                 (historical detections)   (fly.io)  (live ship positions)
                                                                ↓
                                                  Next.js frontend (Vercel)
                                                     /shipnoise    /ais-maps
```

- **Frontend** — Next.js (App Router) + MUI, in `frontend/`, deployed on Vercel. This is the only thing a browser talks to directly.
- **Backend** — FastAPI, in `backend/`, deployed on fly.io. Serves both the historical clip search and the live AIS positions, from two different data sources (see below).
- **Database** — SQLite (`records` table), replicated continuously to S3-compatible storage (Tigris) via [Litestream](https://litestream.io/), so the on-disk fly.io volume isn't a single point of failure.
- **Data collection & processing** — Python scripts in `scripts/`, run continuously on fly.io as a worker process, building the historical detection dataset.

## 2. Data structures and scripts

There are **two independent AIS data paths** feeding the two pages — don't conflate them when debugging:

| | Historical detections (`/shipnoise`) | Live ship traffic (`/ais-maps`) |
|---|---|---|
| Source | [AISstream](https://aisstream.io) websocket | [AISHub](https://www.aishub.net) REST API |
| Credential | `AISSTREAM_API_KEY` | `AISHUB_USERNAME` |
| Where it's used | `scripts/collect/ais_collect.py` | `backend/ais_service.py` |
| Persisted? | Yes — written to the SQLite `records` table | No — kept only in an in-memory, per-process cache |
| Update cadence | Continuous 1-hour collection chunks; processed once daily | Polled on a rolling ~1-min-per-site cycle (AISHub's global rate limit) |

### `records` table (SQLite, schema in `scripts/init_db.py`)

One row per ship-noise detection:

| Column | Meaning |
|---|---|
| `id` | Primary key |
| `date` | UTC date (`YYYYMMDD`) the detection belongs to |
| `site` | Hydrophone site key, e.g. `bush_point` |
| `s3_bucket` | Orcasound S3 bucket prefix for that site's HLS stream |
| `mmsi` | Vessel's AIS MMSI |
| `shipname` | Vessel name, if broadcast |
| `t_cpa` | Timestamp of closest point of approach |
| `confidence` | Ship-noise confidence score |
| `segment_details` | JSON list of the HLS `.ts` segments spanning the detection window |

`backend/api_server.py` derives the playable HLS URL and start/end offsets from `segment_details` at query time — nothing is precomputed or re-encoded.

### `scripts/` — the historical-detection pipeline

Three stages, all parameterized by site via `scripts/config/sites.py` (the single place to add/remove a hydrophone site for this pipeline):

1. **`collect/ais_collect.py`** — one long-lived websocket connection to AISstream, covering all configured sites at once; writes raw AIS messages to JSONL, one UTC-dated folder per site.
2. **`preprocess/get_latest_timestamp.py`** — reads Orcasound's S3 HLS segment filenames to build a timeline, so AIS timestamps can be aligned to actual audio segments.
3. **`process/`** — the core pipeline, run once daily per site:
   - `ais_to_transits.py` — groups raw AIS points by MMSI into vessel "transit" events (entry/exit/CPA relative to the site).
   - `match_all_transits_to_ts.py` — matches each transit's CPA timestamp to the covering HLS stream + offset.
   - `merge_and_dedup.py` — normalizes and deduplicates matched events.
   - `extract_loudest_segment.py` — downloads only the candidate `.ts` segments (never persisted), finds the loudest 30s window, scores confidence, and is the only step that writes into `records`.

`scripts/run_pipeline.py` is the orchestrator that runs on fly.io: it loops AIS collection in 1-hour chunks 24/7, and once a day (default 10:00 UTC, chosen to give a buffer after the Pacific day ends) triggers `preprocess/` then all of `process/` for the previous day, then prunes anything older than `KEEP_DAYS`.

`scripts/init_db.py` creates the `records` table if missing. `scripts/migrate_from_neon.py` is a one-off historical migration script (this project moved from Neon/Postgres to SQLite+Litestream) — not part of normal operation.

### `backend/` — the API the frontend talks to

- **`api_server.py`** — FastAPI app. `/clips/search` and `/vessels/search` query the SQLite `records` table for `/shipnoise`. `/ais/sites` and `/ais/sites/{slug}` expose the live AIS cache for `/ais-maps`.
- **`ais_service.py`** — `AisPoller`, a single background loop that round-robins through every configured site, respecting AISHub's global 1-request-per-minute limit no matter how many frontend clients are polling. A site whose cache is stale gets bumped to the front of the queue on request instead of forcing an extra call.

### `frontend/` — the Next.js app

- `src/app/shipnoise/page.tsx` — the clip search UI (`SelectionPanel`, results, player).
- `src/app/ais-maps/page.tsx` and `src/app/ais-maps/[slug]/page.tsx` — the live traffic grid and per-site fullscreen map (`SiteMap`, Leaflet).
- `src/lib/api.ts` / `src/hooks/useShipnoiseApi.ts` — typed fetch wrappers and React Query hooks for both APIs above.
- `src/lib/sites.ts` — the frontend's own copy of the hydrophone site list (lat/lon, S3 bucket/node name for live audio). Keep in sync with `scripts/config/sites.py` and `backend/ais_service.py`'s `SITES` if you add a site — there are currently three separate site lists in this repo.

### Not part of the running app

The repository root also has a `src/`, `amplify/`, and `public/` (with their own `package.json`) — this is the original Create React App + AWS Amplify prototype, superseded entirely by `frontend/`. It's kept for history only; don't confuse it with the live app when navigating the repo.

## 3. Running it yourself

### Credentials you'll need

| Env var | Used by | Get it from |
|---|---|---|
| `AISHUB_USERNAME` | `backend/` (live map) | Free account at [aishub.net](https://www.aishub.net) |
| `AISSTREAM_API_KEY` | `scripts/` (historical pipeline) | Free API key at [aisstream.io](https://aisstream.io) — only needed if you want to run the collection/processing pipeline, not for the live map |
| `BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL_S3` | Litestream (`litestream.yml`) | Only needed for continuous DB backup in production — skip for local dev |

### Minimal setup: frontend + backend (live AIS map, clip search against an empty DB)

```bash
# Backend
cd backend
pip install -r requirements.txt
```

Create `backend/.env`:

```
AISHUB_USERNAME=your-aishub-username
DATABASE_PATH=./data/shipnoise.db
```

```bash
uvicorn api_server:app --reload --port 8123
```

```bash
# Frontend, in a second terminal
cd frontend
npm install
```

Create `frontend/.env.local`:

```
NEXT_PUBLIC_CLIPS_API_BASE_URL=http://localhost:8123
```

```bash
npm run dev
```

Open `http://localhost:3000/ais-maps` (or `/shipnoise`). The AIS map fills in progressively — AISHub's rate limit means each site refreshes roughly once every N-sites minutes.

### Full pipeline (populate real detections)

```bash
cd scripts
pip install -r requirements.txt
python init_db.py                 # creates the records table at DATABASE_PATH
AISSTREAM_API_KEY=... python run_pipeline.py
```

`run_pipeline.py` runs forever (collection loop + daily processing trigger), matching how it runs on fly.io — for a quick one-off local test of a single stage, call the individual scripts under `collect/`, `preprocess/`, or `process/` directly with `--site`/`--date` flags instead.

Point `backend/.env`'s `DATABASE_PATH` and the pipeline's `DATABASE_PATH` at the same SQLite file so the API can see what the pipeline writes.

### Full stack via Docker (closest to production)

```bash
docker build -f Dockerfile.backend -t shipnoise-backend .
docker run -p 8080:8080 \
  -e AISHUB_USERNAME=... \
  -e AISSTREAM_API_KEY=... \
  shipnoise-backend
```

This runs `start.sh`, which restores the DB from Litestream (if configured), initializes the schema, and starts the API server, the pipeline orchestrator, and Litestream replication together — the same three processes that run in production on fly.io.

## Contributing

Please check out the [CONTRIBUTING doc](https://github.com/orcasound/orca-shipnoise/blob/main/CONTRIBUTING.md) for tips on making a successful contribution.
