
# Shipnoise Backend (FastAPI + PostgreSQL / Neon)

This repository contains the backend services for the Shipnoise project.

The backend provides a FastAPI-based API for querying vessel detections and
serving playback metadata that points directly to Orcasound’s public HLS audio streams.

The database is currently hosted on **Neon (PostgreSQL, provisional choice)**.
There is **no audio storage, no S3 uploads, and no CSV-based ETL pipeline** in the current architecture.

---

## 🔧 Requirements

- Python 3.10+
- PostgreSQL-compatible database (**Neon**, provisional)
- pip + virtualenv (recommended)

---

## 🔐 Environment Variables (`.env`)

Create a `.env` file inside `shipnoise-backend/`:

```

DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:PORT/shipnoise
AISHUB_USERNAME=your-aishub-username

````

> ⚠️ `DATABASE_URL` is required.  
> The backend is currently configured to work with **Neon-hosted PostgreSQL**.

> ℹ️ `AISHUB_USERNAME` is required for the `/ais/sites` endpoints. Without it,
> the AIS polling loop logs a warning and stays idle (cached data stays empty).
> AISHub allows at most one request per minute per account, and that limit is
> enforced globally across all sites by `ais_service.py`, not per site.

Do **NOT** commit `.env` to GitHub (already ignored).

---

## ▶️ Running the API Server (Local Development)

Activate your virtual environment and start FastAPI:

```bash
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
````

Local API base URL:

```
http://localhost:8000
```

---

## ☁️ Deployment (Planned: Fly.io)

The backend is intended to be deployed on **Fly.io** as a long-running FastAPI service.

* No systemd or VM-based process management
* Configuration provided via Fly.io secrets
* FastAPI app exposed directly via Fly.io services

> ℹ️ Deployment to Fly.io has **not been finalized yet**.
> This section documents the intended deployment model only.

---

## 🗃 Database Model (`records` table)

The backend queries a single table containing vessel detections
written directly by upstream processing scripts.

Typical fields include:

| Column          | Description                         |
| --------------- | ----------------------------------- |
| id              | Primary key                         |
| site            | Hydrophone site (lowercase)         |
| date            | Date (YYYYMMDD)                     |
| mmsi            | Vessel MMSI                         |
| shipname        | Vessel name                         |
| t_cpa           | Closest point of approach timestamp |
| confidence      | Detection confidence                |
| s3_bucket       | Orcasound HLS bucket prefix         |
| segment_details | Ordered list of HLS `.ts` segments  |

---

## 🎧 Audio Model

* Audio is **not stored or re-hosted** by Shipnoise
* Playback uses **Orcasound’s public HLS streams**
* The backend returns **direct HTTPS URLs** to `.ts` segments
* The frontend seeks to the center segment for playback

No presigned URLs are generated.

---

## 🚀 API Endpoints

### `GET /clips/search`

Primary (and only) query endpoint used by the frontend.

```
GET /clips/search
  ?shipname=ORCA
  &start_date=2025-11-01
  &end_date=2025-11-30
  &sites=bush_point
  &limit_per_site=5
```

Behavior:

* Supports date ranges and multi-site queries
* Optional vessel name search (`ILIKE`)
* Limits results per site using window functions
* Sites default to all known hydrophones if omitted

---

### `GET /vessels/search`

Autocomplete endpoint for vessel names.

```
GET /vessels/search?q=orca&limit=20
```

Returns a list of matching vessel names.

---

### `GET /ais/sites`

Lists the hydrophone sites tracked for nearby ship traffic (slug, name, lat/lon, search radius).

### `GET /ais/sites/{slug}`

Returns cached AIS vessel positions near one site, e.g. `GET /ais/sites/bush-point`.

```json
{
  "site": "bush-point",
  "updated_at": "2026-07-25T04:12:00+00:00",
  "vessels": [{ "mmsi": 366123456, "name": "EXAMPLE", "lat": 48.03, "lon": -122.60, "sog": 9.4, "cog": 187 }],
  "error": null
}
```

Data comes from a background poller (`ais_service.py`) that round-robins through
all sites at most once per minute (AISHub's global rate limit). Requesting a
site whose cache is missing or more than 90s old bumps it to the front of the
poller's queue instead of forcing an immediate call, so the 1-req/min limit is
never exceeded no matter how many clients ask.

---

## 🧭 Data Flow Summary

```
Processing scripts
   ↓
Neon PostgreSQL (records)
   ↓
FastAPI backend
   ↓
Frontend (HLS playback via Orcasound)
```

---

## 📝 Notes

* The backend is read-only with respect to detections
* All writes happen upstream in processing scripts
* Audio URLs always reference Orcasound’s canonical infrastructure
* Missing results usually indicate no detections for the requested range

---

## 📄 License

MIT License
Copyright © 2025

```
```
