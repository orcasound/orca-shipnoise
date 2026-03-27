#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export timestamps for a target UTC date for all Orcasound sites.

Handles multiple HLS sessions per day (e.g. after stream restarts).
Results are stored under:
    Sites/timestamps/<YYYYMMDD>/<site>_<YYYYMMDD>_timestamps_UTC.txt
"""

import argparse
import os
import re
import sys
import boto3
from botocore import UNSIGNED
from botocore.client import Config
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List

from config.sites import KEY_TO_HLS, S3_BUCKET, STALE_THRESHOLD_DAYS

# ---------- SETTINGS ----------
BUCKET = S3_BUCKET
SEG_DUR = 10  # seconds per .ts segment

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Sites"))
OUTPUT_ROOT = os.path.join(BASE_DIR, "timestamps")

SITES = KEY_TO_HLS

# ---------- S3 CLIENT ----------
s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
_NUMERIC_RE = re.compile(r".*/hls/(\d+)/$")


def list_numeric_subfolders(bucket: str, base_prefix: str) -> List[str]:
    paginator = s3.get_paginator("list_objects_v2")
    folders = []
    for page in paginator.paginate(Bucket=bucket, Prefix=base_prefix, Delimiter="/"):
        for pref in page.get("CommonPrefixes", []):
            m = _NUMERIC_RE.match(pref.get("Prefix", ""))
            if m:
                folders.append(m.group(1))
    folders.sort(key=lambda x: int(x))
    return folders


def fetch_timestamps_for_folder(bucket: str, full_prefix: str) -> List[str]:
    """Fetch all .ts timestamps under a given S3 prefix."""
    paginator = s3.get_paginator("list_objects_v2")
    lines = []
    for page in paginator.paginate(Bucket=bucket, Prefix=full_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".ts"):
                continue
            start_utc = obj["LastModified"].astimezone(timezone.utc)
            end_utc = start_utc + timedelta(seconds=SEG_DUR)
            lines.append(f"{key},{start_utc.isoformat()},{end_utc.isoformat()}")
    return lines


def export_for_date(site: str, base_prefix: str, target_date: date) -> Optional[str]:
    """Find all HLS sessions for target_date and save combined timestamps."""
    all_folders = list_numeric_subfolders(BUCKET, base_prefix)

    # Include sessions started within [target_date - 1 day, target_date + 1 day)
    # to catch PST sessions that started before UTC midnight of target_date
    window_start = datetime.combine(
        target_date - timedelta(days=1), datetime.min.time()
    ).replace(tzinfo=timezone.utc)
    window_end = datetime.combine(
        target_date + timedelta(days=1), datetime.min.time()
    ).replace(tzinfo=timezone.utc)

    matching = [
        fid for fid in all_folders
        if window_start <= datetime.fromtimestamp(int(fid), tz=timezone.utc) < window_end
    ]

    if not matching:
        print(f"⚠️ No HLS sessions found for {site} on {target_date}")
        return None

    print(f"  Found {len(matching)} session(s): {matching}")

    all_lines = []
    for fid in matching:
        lines = fetch_timestamps_for_folder(BUCKET, f"{base_prefix}{fid}/")
        all_lines.extend(lines)

    if not all_lines:
        print(f"⚠️ No .ts files found for {site} on {target_date}")
        return None

    all_lines.sort(key=lambda x: x.split(",")[1])

    date_str = target_date.strftime("%Y%m%d")
    out_dir = os.path.join(OUTPUT_ROOT, date_str)
    os.makedirs(out_dir, exist_ok=True)

    out_file = os.path.join(out_dir, f"{site}_{date_str}_timestamps_UTC.txt")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(all_lines))

    print(f"✅ Saved {len(all_lines)} entries → {out_file}")

    days_old = (date.today() - target_date).days
    if days_old > STALE_THRESHOLD_DAYS:
        print(f"⚠️  WARNING: {site} timestamps are {days_old} days old. "
              f"Hydrophone may be offline.")

    return out_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Target UTC date YYYYMMDD (default: yesterday)")
    args = parser.parse_args()

    if args.date:
        target_date = datetime.strptime(args.date, "%Y%m%d").date()
    else:
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    print(f"🚀 Exporting timestamps for {target_date.strftime('%Y%m%d')}…")
    results = []
    for site, prefix in SITES.items():
        print(f"\n▶ {site}")
        path = export_for_date(site, prefix, target_date)
        if path:
            results.append(path)

    print("\n🎯 Done.")
    for p in results:
        print("  -", p)


if __name__ == "__main__":
    main()
