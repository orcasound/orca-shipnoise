#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export latest *complete* day timestamps for all Orcasound sites.
Each site's most recent *complete* day is the penultimate HLS folder.
Results are stored under:
    Sites/timestamps/<date>/<site>_<folder_id>_<date>_timestamps_UTC.txt
"""

import os
import re
import boto3
from botocore import UNSIGNED
from botocore.client import Config
from datetime import timedelta, timezone
from typing import Optional, List
import datetime

# ---------- SETTINGS ----------
BUCKET = "audio-orcasound-net"
SEG_DUR = 10  # seconds per .ts segment

# auto-detect project base
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Sites"))
OUTPUT_ROOT = os.path.join(BASE_DIR, "timestamps")

SITES = {
    "bush_point":     "rpi_bush_point/hls/",
    "orcasound_lab":  "rpi_orcasound_lab/hls/",
    "port_townsend":  "rpi_port_townsend/hls/",
    "sunset_bay":     "rpi_sunset_bay/hls/",
}

# ---------- S3 CLIENT ----------
s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
_NUMERIC_RE = re.compile(r".*/hls/(\d+)/$")


# ---------- FUNCTIONS ----------

def list_numeric_subfolders(bucket: str, base_prefix: str) -> List[str]:
    """List numeric subfolders under rpi_<site>/hls/."""
    paginator = s3.get_paginator("list_objects_v2")
    folders = []
    for page in paginator.paginate(Bucket=bucket, Prefix=base_prefix, Delimiter="/"):
        for pref in page.get("CommonPrefixes", []):
            m = _NUMERIC_RE.match(pref.get("Prefix", ""))
            if m:
                folders.append(m.group(1))
    folders.sort(key=lambda x: int(x))
    return folders


def pick_latest_complete_folder(bucket: str, base_prefix: str) -> Optional[str]:
    """Pick the second newest numeric folder as the 'latest complete' day."""
    folders = list_numeric_subfolders(bucket, base_prefix)
    if len(folders) < 2:
        return None
    return folders[-2]


def export_timestamp_for_prefix(bucket: str, full_prefix: str, seg_dur: int):
    """Export all .ts timestamps (UTC) under given prefix."""
    paginator = s3.get_paginator("list_objects_v2")
    lines = []
    first_time = None

    print(f"Listing objects under: s3://{bucket}/{full_prefix}")

    for page in paginator.paginate(Bucket=bucket, Prefix=full_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".ts"):
                continue
            start_utc = obj["LastModified"].astimezone(timezone.utc)
            end_utc = start_utc + timedelta(seconds=seg_dur)
            lines.append(f"{key},{start_utc.isoformat()},{end_utc.isoformat()}")
            if first_time is None:
                first_time = start_utc  # use first .ts as start-of-day marker

    lines.sort(key=lambda x: x.split(",")[1])

    # determine date from first .ts timestamp
    if first_time:
        date_str = first_time.date().isoformat()
    else:
        date_str = datetime.date.today().isoformat()

    return lines, date_str


def export_latest_complete_for_site(site: str, base_prefix: str):
    """Pick latest complete folder and export timestamp file with date in name."""
    folder_id = pick_latest_complete_folder(BUCKET, base_prefix)
    if not folder_id:
        print(f"⚠️ Not enough folders for site={site}")
        return None

    full_prefix = f"{base_prefix}{folder_id}/"
    lines, date_str = export_timestamp_for_prefix(BUCKET, full_prefix, SEG_DUR)

    # ✅ new path: /Sites/timestamps/<date>/
    out_dir = os.path.join(OUTPUT_ROOT, date_str)
    os.makedirs(out_dir, exist_ok=True)

    out_file = os.path.join(
        out_dir,
        f"{site}_{folder_id}_{date_str}_timestamps_UTC.txt"
    )

    content = "\n".join(lines)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Saved {len(lines)} entries → {out_file}")

    return out_file


# ---------- MAIN ----------
def main():
    print("🚀 Exporting latest *complete* day timestamps for all sites…")
    results = []
    for site, prefix in SITES.items():
        print(f"\n▶ {site}")
        path = export_latest_complete_for_site(site, prefix)
        if path:
            results.append(path)

    print("\n🎯 Done.")
    for p in results:
        print("  -", p)


if __name__ == "__main__":
    main()
