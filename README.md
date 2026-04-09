# shipnoise.net

A web application for visualizing and listening to underwater ship noise recorded by [Orcasound](https://orcasound.net) hydrophones in the Salish Sea. The goal is to help understand and reduce noise pollution for the endangered Southern Resident killer whales.

## Architecture

```
Orcasound GraphQL API  →  AIS data collection scripts  →  SQLite (fly.io)
                                                                  ↓
                                                   FastAPI backend (fly.io)
                                                                  ↓
                                                    Next.js frontend (frontend/)
```

- **Frontend** — Next.js (App Router) + MUI, located in `frontend/`
- **Backend** — FastAPI serving REST API, located in `backend/`
- **Database** — SQLite, replicated via Litestream to Tigris (S3-compatible)
- **Deployment** — fly.io (`fly.toml`)
- **Data collection** — Python scripts in `scripts/` that pull AIS ship data and match it against Orcasound hydrophone recordings

## Running locally

### Frontend

```bash
cd frontend
npm install
```

Create a `.env.local` file:

```
NEXT_PUBLIC_CLIPS_API_BASE_URL=https://orca-shipnoise-sjdtow.fly.dev/
```

Then run:

```bash
npm run dev
```

Open [http://localhost:3000/shipnoise](http://localhost:3000/shipnoise) in your browser.

### Backend

```bash
pip install -r backend/requirements.txt
DATABASE_PATH=./data/shipnoise.db uvicorn backend.api_server:app --reload
```

## Contributing

Please check out the [CONTRIBUTING doc](https://github.com/orcasound/orca-shipnoise/blob/main/CONTRIBUTING.md) for tips on making a successful contribution.
