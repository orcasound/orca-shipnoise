from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, create_engine
from typing import List
import os
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- Database Connection ---
DB_URL = os.getenv("DATABASE_URL")
engine = create_engine(DB_URL, pool_pre_ping=True)

# --- Constants ---
ORCASOUND_BASE_URL = "https://audio-orcasound-net.s3.amazonaws.com"

# FIX: Updated to lowercase to match the PostgreSQL database values
DEFAULT_SITES = ["bush_point", "orcasound_lab", "port_townsend", "sunset_bay"]

# --- Helper Function ---
def generate_public_urls(s3_bucket, segment_details):
    """
    Generates a list of direct HTTPS URLs for Orcasound S3 bucket.
    """
    if not s3_bucket or not segment_details:
        return []
    
    # Handle case where database returns a JSON string instead of list
    if isinstance(segment_details, str):
        try:
            segment_details = json.loads(segment_details)
        except:
            return []

    urls = []
    if isinstance(segment_details, list):
        for segment in segment_details:
            # Construct the full public URL
            url = f"{ORCASOUND_BASE_URL}/{s3_bucket}/hls/{segment}"
            urls.append(url)
    return urls

# ============================================================
#  ENDPOINT: Get Clips (Legacy/Direct)
# ============================================================
@app.get("/clips")
def get_clips(
    site: str = Query(...),
    date: str = Query(..., description="YYYYMMDD or YYYY-MM-DD"),
    limit: int = Query(200, ge=1, le=500),
):
    sql = """
        SELECT
            id,
            site,
            date,
            mmsi,
            shipname,
            t_cpa,
            confidence,
            s3_bucket,
            segment_details
        FROM records
        WHERE site = :site
          AND date = :date
        ORDER BY t_cpa DESC NULLS LAST
        LIMIT :limit;
    """

    # FIX: Force site to lowercase and remove dashes from date to match DB format
    params = {
        "site": site.lower(), 
        "date": date.replace("-", ""), 
        "limit": limit
    }

    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    results = []
    for row in rows:
        public_urls = generate_public_urls(row["s3_bucket"], row["segment_details"])
        results.append({
            **row,
            "audio_urls": public_urls,
            "center_segment_index": 1
        })

    return {
        "count": len(results),
        "site": site,
        "date": date,
        "results": results,
    }

# ============================================================
#  ENDPOINT: Search Clips (Main Search)
# ============================================================
@app.get("/clips/search")
def search_clips(
    shipname: str = Query(None),
    start_date: str = Query(...),
    end_date: str = Query(...),
    sites: List[str] = Query(None),
    limit_per_site: int = Query(5, ge=1, le=50),
):
    if sites is None:
        sites = DEFAULT_SITES
    else:
        # FIX: Ensure all requested sites are lowercase
        sites = [s.lower() for s in sites]

    sql = """
        SELECT * FROM (
            SELECT 
                id,
                site,
                date,
                mmsi,
                shipname,
                t_cpa,
                confidence,
                s3_bucket,
                segment_details,
                ROW_NUMBER() OVER (
                    PARTITION BY site
                    ORDER BY t_cpa DESC
                ) AS rk
            FROM records
            WHERE site = ANY(:sites)
              AND date BETWEEN :start AND :end
              AND (:ship IS NULL OR shipname ILIKE :ship)
        ) ranked
        WHERE rk <= :limit_per_site
        ORDER BY site, t_cpa DESC;
    """

    # Format parameters for DB
    p_start = start_date.replace("-", "")
    p_end = end_date.replace("-", "")
    p_ship = f"%{shipname}%" if shipname else None

    params = {
        "sites": sites,
        "start": p_start,
        "end": p_end,
        "ship": p_ship,
        "limit_per_site": limit_per_site,
    }

    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    results = []
    for row in rows:
        public_urls = generate_public_urls(row["s3_bucket"], row["segment_details"])
        results.append({
            **row,
            "audio_urls": public_urls,
            "center_segment_index": 1
        })

    return {
        "count": len(results),
        "start_date": start_date,
        "end_date": end_date,
        "shipname_query": shipname,
        "sites": sites,
        "limit_per_site": limit_per_site,
        "results": results,
    }

# ============================================================
#  ENDPOINT: Vessel Autocomplete
# ============================================================
@app.get("/vessels/search")
def vessel_suggestions(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50)
):
    sql = """
        SELECT DISTINCT shipname
        FROM records
        WHERE shipname ILIKE :q
        ORDER BY shipname ASC
        LIMIT :limit;
    """
    params = {"q": f"%{q}%", "limit": limit}
    
    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).fetchall()
        
    results = [r[0] for r in rows]
    return {"results": results}
