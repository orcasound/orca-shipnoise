from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Query
from sqlalchemy import text, create_engine
from typing import List
import boto3
from botocore.client import Config
import os

app = FastAPI()

# --- Load environment variables ---
DB_URL = os.getenv("DATABASE_URL")

BUCKET = os.getenv("AWS_S3_BUCKET", "shipnoise-data")
REGION = os.getenv("AWS_REGION", "us-east-2")

# --- Create SQLAlchemy engine ---
engine = create_engine(DB_URL, pool_pre_ping=True)

# --- S3 client ---
s3 = boto3.client(
    "s3",
    region_name=REGION,
    config=Config(signature_version="s3v4")
)

DEFAULT_SITES = ["Bush_Point", "Orcasound_Lab", "Port_Townsend", "Sunset_Bay"]


# ============================================================
#  LEGACY ENDPOINT (Front-end still uses this)
#  /clips?site=Bush_Point&date=2025-10-30&limit=200
# ============================================================
@app.get("/clips")
def get_clips(
    site: str = Query(...),
    date: str = Query(..., description="YYYY-MM-DD"),
    limit: int = Query(200, ge=1, le=500),
):
    sql = """
        SELECT
            site,
            date_utc,
            mmsi,
            shipname,
            t_cpa,
            cpa_distance_m,
            loudness_db,
            aws_bucket,
            aws_key,
            loudest_ts
        FROM clips
        WHERE site = :site
          AND date_utc = :date
        ORDER BY loudness_db DESC NULLS LAST
        LIMIT :limit;
    """

    params = {"site": site, "date": date, "limit": limit}

    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    # Attach presigned URLs
    results = []
    for row in rows:
        presigned = None
        if row["aws_key"]:
            try:
                presigned = s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": row["aws_bucket"], "Key": row["aws_key"]},
                    ExpiresIn=3600,
                )
            except Exception as exc:
                print(f"[WARN] Presign failed for {row['aws_key']}: {exc}")

        results.append({**row, "presigned_url": presigned})

    return {
        "count": len(results),
        "site": site,
        "date": date,
        "results": results,
    }


# ============================================================
#  NEW ENDPOINT: /clips/search (for future)
# ============================================================
@app.get("/clips/search")
def search_clips(
    shipname: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    sites: List[str] = Query(None),
    limit_per_site: int = Query(5, ge=1, le=50),
):
    if sites is None:
        sites = DEFAULT_SITES

    sql = """
        SELECT * FROM (
            SELECT site,
                   date_utc,
                   mmsi,
                   shipname,
                   t_cpa,
                   loudest_ts,
                   cpa_distance_m,
                   loudness_db,
                   aws_key,
                   aws_bucket,
                   ROW_NUMBER() OVER (
                       PARTITION BY site
                       ORDER BY date_utc DESC, loudness_db DESC
                   ) AS rk
            FROM clips
            WHERE site = ANY(:sites)
              AND date_utc BETWEEN :start AND :end
              AND shipname ILIKE :ship
        ) ranked
        WHERE rk <= :limit_per_site
        ORDER BY site, date_utc DESC, loudness_db DESC;
    """

    pg_sites = "{" + ",".join(sites) + "}"
    params = {
        "sites": sites,
        "start": start_date,
        "end": end_date,
        "ship": f"%{shipname}%",
        "limit_per_site": limit_per_site,
    }

    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    results = []
    for row in rows:
        presigned = None
        if row["aws_key"]:
            try:
                presigned = s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": row["aws_bucket"], "Key": row["aws_key"]},
                    ExpiresIn=3600,
                )
            except Exception as exc:
                print(f"[WARN] Presign failed for {row['aws_key']}: {exc}")

        results.append({**row, "presigned_url": presigned})

    return {
        "count": len(results),
        "start_date": start_date,
        "end_date": end_date,
        "shipname_query": shipname,
        "sites": sites,
        "limit_per_site": limit_per_site,
        "results": results,
    }
@app.get("/vessels/search")
def vessel_suggestions(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50)
):
    """
    Return distinct ship names for autocomplete suggestions.
    """
    sql = """
        SELECT DISTINCT shipname
        FROM clips
        WHERE shipname ILIKE :q
        ORDER BY shipname ASC
        LIMIT :limit;
    """

    params = {"q": f"%{q}%", "limit": limit}

    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).fetchall()

    results = [r[0] for r in rows]

    return {"results": results}
