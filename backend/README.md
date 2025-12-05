# Shipnoise Backend (FastAPI + PostgreSQL + AWS S3)

This repository contains the backend services for the Shipnoise project, including:

- FastAPI API server  
- ETL pipelines that ingest audio/ship AIS metadata from AWS S3 into PostgreSQL  
- Local development tools and environment configuration

The backend is used by the Shipnoise frontend to fetch vessel audio clip metadata and presigned S3 audio URLs.

---

## 📦 Folder Structure

```
shipnoise-backend/
│
├── api_server.py                 # FastAPI application
├── etl_from_loudness_summary.py  # ETL script for a single day's CSV
├── etl_import_all_from_s3.py     # ETL script that scans and imports all dates
├── .env                          # Environment variables (NOT committed)
├── .gitignore                    # Ignore file for Git commit hygiene
└── README.md                     # Documentation
```

---

## 🔧 Requirements

- Python 3.10+
- PostgreSQL
- AWS account (S3 + IAM)
- pip + virtualenv recommended

---

## 🔐 Environment Variables (`.env`)

Create a `.env` file inside `shipnoise-backend/`:

```
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@localhost:5432/shipnoise
AWS_REGION=us-east-2
AWS_S3_BUCKET=shipnoise-data
PRESIGN_EXPIRES_SECONDS=900
ALLOWED_ORIGINS=http://localhost:3000
```

> ⚠️ The backend uses **DATABASE_URL**, so make sure this key exists.

Do **NOT** commit `.env` to GitHub (already ignored in `.gitignore`).

---

## ▶️ Running the API Server (Local Development)

Activate your virtual environment and start FastAPI:

```bash
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
```

Local API base URL:

```
http://localhost:8000
```

### Example request  
(Replace `YYYY-MM-DD` with any date that exists in your local database)

```
http://localhost:8000/clips?site=Bush_Point&date=YYYY-MM-DD
```

> ℹ️ **Note:**  
> The frontend typically queries only within a recent **30-day window**, so in most cases the date must fall within that range to return results.

---

## 🌐 Production / Staging Deployment

This backend is deployed on an AWS EC2 instance and managed by `systemd`.

### systemd service example (`shipnoise-backend.service`)

```
[Service]
WorkingDirectory=/home/ubuntu/shipnoise-backend
EnvironmentFile=/home/ubuntu/shipnoise-backend/.env
Environment="PATH=/home/ubuntu/shipnoise-backend/.venv/bin"
ExecStart=/home/ubuntu/shipnoise-backend/.venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000
Restart=always
```

Restart after deployment:

```bash
sudo systemctl daemon-reload
sudo systemctl restart shipnoise-backend
sudo systemctl status shipnoise-backend
```

> ⚠️ Production deployments **do not** use `localhost:8000`.  
> Replace it with the server’s **public IP or domain** (e.g. http://18.220.84.169:8000).

---

## 📊 ETL Scripts

### 1️⃣ `etl_from_loudness_summary.py`
Reads:

```
s3://<AWS_S3_BUCKET>/audio/<Site>/<YYYYMMDD>/loudness_summary_<YYYYMMDD>.csv
```

Then parses and **upserts** rows into the PostgreSQL `clips` table.

Usage:

```bash
python etl_from_loudness_summary.py --site Bush_Point_data --date 20251120
```

### 2️⃣ `etl_import_all_from_s3.py`
Automatically scans S3 for all available dates for all sites and imports them.

```
python etl_import_all_from_s3.py
```

---

## 🗃 Table: `clips`

The ETL pipeline writes into:

| Column           | Description |
|------------------|-------------|
| id               | UUID key combining site/date/mmsi/aws_key |
| site             | Hydrophone site |
| date_utc         | Date (UTC) |
| mmsi             | Vessel MMSI |
| shipname         | Vessel name |
| t_cpa            | Closest-approach timestamp |
| cpa_distance_m   | Distance at CPA |
| aws_bucket       | S3 bucket name |
| aws_key          | Path to WAV audio |
| loudest_ts       | Timestamp of loudest segment |
| loudness_db      | max_volume_db or mean_volume_db |

---

## 🚀 API Endpoints

### `/clips`
Legacy endpoint used by the frontend.

```
GET /clips?site=Bush_Point&date=YYYY-MM-DD&limit=200
```

Returns presigned S3 audio URLs.

---

### `/clips/search`
Future enhanced search endpoint.

```
GET /clips/search?shipname=ORCA&start_date=2025-11-01&end_date=2025-11-30&sites=Bush_Point&limit_per_site=5
```

---

### `/vessels/search`
Used for autocomplete suggestions.

```
GET /vessels/search?q=orca&limit=20
```

---

## 📝 Notes

- The project stores and queries **only recent data (≈30 days)** by design.  
- Missing results usually mean no data available for the requested date/site.  
- For production, ensure NGINX reverse proxy routes `/clips` to port `8000`.

---

## 🤝 Contributing

Pull requests, issues, and improvements are welcome!  
This repository is intended to serve as a clean, documented backend foundation for the larger Shipnoise project.

---

## 📄 License

MIT License  
Copyright © 2025  
