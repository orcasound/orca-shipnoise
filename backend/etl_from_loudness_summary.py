#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETL (S3-driven): read loudness_summary_<YYYYMMDD>.csv from:
  s3://{AWS_S3_BUCKET}/audio/<SiteFolder>/<YYYYMMDD>/
"""

import argparse
import io
import os
import re
import sys
import uuid
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from botocore.client import Config
import boto3
from dotenv import load_dotenv
from urllib.parse import urlparse
from datetime import datetime, timezone

# --- Load .env ---
load_dotenv()
BUCKET = os.getenv("AWS_S3_BUCKET", "shipnoise-data")
DB_URL = os.getenv("DATABASE_URL")
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")

if not DB_URL:
    print("ERROR: DATABASE_URL is not set.", file=sys.stderr)
    sys.exit(1)

SITE_MAP = {
    "Bush_Point_data": "Bush_Point",
    "Orcasound_Lab_data": "Orcasound_Lab",
    "Port_Townsend_data": "Port_Townsend",
    "Sunset_Bay_data": "Sunset_Bay",
}
ALL_SITES = list(SITE_MAP.keys())

engine: Engine = create_engine(DB_URL, pool_pre_ping=True)
s3 = boto3.client("s3", region_name=AWS_REGION, config=Config(signature_version="s3v4"))


def map_date(date_raw: str | None) -> str | None:
    if not date_raw:
        return None
    s = str(date_raw).strip()
    try:
        return pd.to_datetime(s, format="%Y%m%d").date().isoformat()
    except Exception:
        try:
            return pd.to_datetime(s).date().isoformat()
        except Exception:
            return None


def basename_from_output_audio(val: str | None) -> str | None:
    if not val or not isinstance(val, str):
        return None
    s = val.strip()
    if "://" in s:
        parsed = urlparse(s)
        s = os.path.basename(parsed.path)
    else:
        s = os.path.basename(s)
    return s if s.lower().endswith(".wav") else None


def s3_read_csv(key: str) -> pd.DataFrame | None:
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=key)
        return pd.read_csv(io.BytesIO(obj["Body"].read()))
    except s3.exceptions.NoSuchKey:
        print(f"[WARN] missing CSV: s3://{BUCKET}/{key}")
        return None
    except Exception as e:
        print(f"[ERROR] get_object failed: s3://{BUCKET}/{key} :: {e}")
        return None


def upsert_row(row: dict):
    if row.get("date_utc"):
        try:
            row["date_utc"] = pd.to_datetime(row["date_utc"]).date()
        except Exception:
            pass
    if row.get("t_cpa"):
        try:
            row["t_cpa"] = pd.to_datetime(row["t_cpa"])
        except Exception:
            pass

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO clips (
              id, site, date_utc, mmsi, shipname, t_cpa, cpa_distance_m,
              aws_bucket, aws_key, segment_range, loudest_ts, loudness_db
            )
            VALUES (
              :id, :site, :date_utc, :mmsi, :shipname, :t_cpa, :cpa_distance_m,
              :aws_bucket, :aws_key, :segment_range, :loudest_ts, :loudness_db
            )
            ON CONFLICT (id) DO UPDATE
            SET shipname       = EXCLUDED.shipname,
                cpa_distance_m = EXCLUDED.cpa_distance_m,
                aws_key        = EXCLUDED.aws_key,
                loudest_ts     = EXCLUDED.loudest_ts,
                loudness_db    = EXCLUDED.loudness_db;
        """), row)


def ingest_one_day_for_site(site_key: str, ymd: str) -> tuple[int, int]:
    site_folder = SITE_MAP.get(site_key, site_key.replace("_data", ""))
    csv_key = f"audio/{site_folder}/{ymd}/loudness_summary_{ymd}.csv"
    df = s3_read_csv(csv_key)
    if df is None:
        print(f"[{site_folder} {ymd}] no CSV found, skip.")
        return 0, 0

    df.columns = [c.strip() for c in df.columns]
    for col in ["date", "mmsi", "shipname", "t_cpa", "cpa_distance_m",
                "segment_range", "loudest_seg", "mean_volume_db", "max_volume_db",
                "output_audio"]:
        if col not in df.columns:
            df[col] = None

    inserted = skipped = 0

    for idx, r in df.iterrows():
        try:
            date_utc = map_date(r.get("date"))
            mmsi = str(r.get("mmsi")).split(".")[0].strip() if pd.notna(r.get("mmsi")) else None
            shipname = str(r.get("shipname")).strip() if pd.notna(r.get("shipname")) else ""
            t_cpa = str(r.get("t_cpa")).strip() if pd.notna(r.get("t_cpa")) else None
            cpa_distance_m = int(float(r.get("cpa_distance_m"))) if pd.notna(r.get("cpa_distance_m")) else None
            segment_range = str(r.get("segment_range")).strip() if pd.notna(r.get("segment_range")) else None
            loudest_ts = str(r.get("loudest_seg")).strip() if pd.notna(r.get("loudest_seg")) else None

            loudness_db = None
            if pd.notna(r.get("max_volume_db")):
                loudness_db = float(r.get("max_volume_db"))
            elif pd.notna(r.get("mean_volume_db")):
                loudness_db = float(r.get("mean_volume_db"))

            basename = basename_from_output_audio(r.get("output_audio"))
            aws_key = f"audio/{site_folder}/{ymd}/{basename}" if basename else None

            missing = []
            if not date_utc: missing.append("date")
            if not mmsi:     missing.append("mmsi")
            if not t_cpa:    missing.append("t_cpa")
            if not aws_key:  missing.append("aws_key(basename)")

            if missing:
                if skipped < 10:
                    print(f"[SKIP] {site_folder} {ymd} row#{idx}: missing {','.join(missing)}; output_audio='{r.get('output_audio')}'")
                skipped += 1
                continue

            row = {
                "id": uuid.uuid5(uuid.NAMESPACE_URL, f"{site_folder}|{date_utc}|{mmsi}|{aws_key}").hex,
                "site": site_folder,
                "date_utc": date_utc,
                "mmsi": mmsi,
                "shipname": shipname,
                "t_cpa": t_cpa,
                "cpa_distance_m": cpa_distance_m,
                "aws_bucket": BUCKET,
                "aws_key": aws_key,
                "segment_range": segment_range,
                "loudest_ts": loudest_ts,
                "loudness_db": loudness_db,
            }
            upsert_row(row)
            inserted += 1
        except Exception as e:
            if skipped < 10:
                print(f"[SKIP-ERR] {site_folder} {ymd} row#{idx}: {e}")
            skipped += 1

    print(f"[{site_folder} {ymd}] inserted={inserted}, skipped={skipped}")
    return inserted, skipped


def get_latest_date_for_site(site_folder: str) -> str | None:
    """Find latest YYYYMMDD folder under audio/<site_folder>/"""
    prefix = f"audio/{site_folder}/"
    try:
        resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix, Delimiter="/")
        dates = []
        for c in resp.get("CommonPrefixes", []):
            folder = c["Prefix"].split("/")[-2]
            if re.fullmatch(r"\d{8}", folder):
                dates.append(folder)
        return max(dates) if dates else None
    except Exception as e:
        print(f"[WARN] Could not list S3 folders for {site_folder}: {e}")
        return None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="S3-driven ETL for loudness_summary CSVs.")
    g = p.add_mutually_exclusive_group(required=False)
    g.add_argument("--site", nargs="+", help="Sites e.g. Bush_Point_data Sunset_Bay_data")
    g.add_argument("--site-all", action="store_true", help="Use all known sites")
    p.add_argument("--date", nargs="+", help="YYYYMMDD (optional, auto-detect latest if not given)")
    return p.parse_args()


def main():
    args = parse_args()
    sites = ALL_SITES if (args.site_all or not args.site) else args.site

    total_ins = total_skp = 0
    for s in sites:
        site_folder = SITE_MAP.get(s, s.replace("_data", ""))
        if not args.date:
            latest = get_latest_date_for_site(site_folder)
            if not latest:
                print(f"[WARN] No date folders found for {site_folder}, skip.")
                continue
            dates = [latest]
            print(f"[AUTO] Using latest date {latest} for {site_folder}")
        else:
            dates = args.date

        for ymd in dates:
            if not re.fullmatch(r"\d{8}", ymd):
                print(f"WARNING: skip invalid date '{ymd}' (expect YYYYMMDD)", file=sys.stderr)
                continue
            ins, skp = ingest_one_day_for_site(s, ymd)
            total_ins += ins
            total_skp += skp

    print(f"DONE. total_inserted={total_ins}, total_skipped={total_skp}")


if __name__ == "__main__":
    main()
