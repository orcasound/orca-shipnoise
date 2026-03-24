from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import json
import re
import sqlite3

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Connection ---
DB_PATH = os.getenv("DATABASE_PATH", "/app/data/shipnoise.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- Constants ---
ORCASOUND_BASE_URL = "https://audio-orcasound-net.s3.amazonaws.com"
SEG_DUR = 10  # seconds per .ts segment

DEFAULT_SITES = ["bush_point", "orcasound_lab", "port_townsend", "sunset_bay"]

# --- Helper Function ---
def parse_hls_info(s3_bucket, segment_details):
    """
    Derives HLS manifest URL and playback offsets from segment_details.
    segment format: "1539203407/live004.ts"
    Returns (hls_url, start_offset_sec, end_offset_sec) or (None, None, None).
    """
    if not s3_bucket or not segment_details:
        return None, None, None

    if isinstance(segment_details, str):
        try:
            segment_details = json.loads(segment_details)
        except Exception:
            return None, None, None

    if not isinstance(segment_details, list) or not segment_details:
        return None, None, None

    seg_nums = []
    folder_id = None
    for seg in segment_details:
        m = re.match(r'^(\d+)/live(\d+)\.ts$', str(seg))
        if m:
            if folder_id is None:
                folder_id = m.group(1)
            seg_nums.append(int(m.group(2)))

    if folder_id is None or not seg_nums:
        return None, None, None

    hls_url = f"{ORCASOUND_BASE_URL}/{s3_bucket}/hls/{folder_id}/live.m3u8"
    start_offset_sec = min(seg_nums) * SEG_DUR
    end_offset_sec = (max(seg_nums) + 1) * SEG_DUR
    return hls_url, start_offset_sec, end_offset_sec


def generate_public_urls(s3_bucket, segment_details):
    """
    Generates a list of direct HTTPS URLs for Orcasound S3 bucket.
    """
    if not s3_bucket or not segment_details:
        return []

    if isinstance(segment_details, str):
        try:
            segment_details = json.loads(segment_details)
        except:
            return []

    urls = []
    if isinstance(segment_details, list):
        for segment in segment_details:
            url = f"{ORCASOUND_BASE_URL}/{s3_bucket}/hls/{segment}"
            urls.append(url)
    return urls


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
        sites = [s.lower() for s in sites]

    site_params = {f"site_{i}": s for i, s in enumerate(sites)}
    site_placeholders = ",".join(f":site_{i}" for i in range(len(sites)))

    sql = f"""
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
            WHERE site IN ({site_placeholders})
              AND date BETWEEN :start AND :end
              AND (:ship IS NULL OR LOWER(shipname) LIKE LOWER(:ship))
        ) ranked
        WHERE rk <= :limit_per_site
        ORDER BY site, t_cpa DESC;
    """

    p_start = start_date.replace("-", "")
    p_end = end_date.replace("-", "")
    p_ship = f"%{shipname}%" if shipname else None

    params = {
        **site_params,
        "start": p_start,
        "end": p_end,
        "ship": p_ship,
        "limit_per_site": limit_per_site,
    }

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    results = []
    for row in rows:
        row_dict = dict(row)
        public_urls = generate_public_urls(row_dict["s3_bucket"], row_dict["segment_details"])
        hls_url, start_offset_sec, end_offset_sec = parse_hls_info(row_dict["s3_bucket"], row_dict["segment_details"])
        results.append({
            **row_dict,
            "audio_urls": public_urls,
            "hls_url": hls_url,
            "start_offset_sec": start_offset_sec,
            "end_offset_sec": end_offset_sec,
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
        WHERE LOWER(shipname) LIKE LOWER(:q)
        ORDER BY shipname ASC
        LIMIT :limit;
    """
    params = {"q": f"%{q}%", "limit": limit}

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    results = [r[0] for r in rows]
    return {"results": results}
