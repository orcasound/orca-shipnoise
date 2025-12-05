#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto-import all available loudness_summary_<YYYYMMDD>.csv files from S3.
Scans every site folder and loads each CSV into the PostgreSQL 'clips' table.
Skips missing or invalid files.
"""

import os
import re
import subprocess
from dotenv import load_dotenv

load_dotenv()

SITES = ["Bush_Point", "Orcasound_Lab", "Port_Townsend", "Sunset_Bay"]
BUCKET = os.getenv("AWS_S3_BUCKET", "shipnoise-data")

def list_s3_csvs(site):
    """Return all loudness_summary CSV keys under audio/<site>/"""
    try:
        result = subprocess.run(
            ["aws", "s3", "ls", f"s3://{BUCKET}/audio/{site}/", "--recursive"],
            capture_output=True, text=True, check=True
        )
        csvs = []
        for line in result.stdout.splitlines():
            if "loudness_summary_" in line and line.strip().endswith(".csv"):
                # extract date like 20251108
                m = re.search(r"loudness_summary_(\d{8})\.csv", line)
                if m:
                    csvs.append(m.group(1))
        return sorted(set(csvs))
    except subprocess.CalledProcessError as e:
        print(f"[WARN] failed to list {site}: {e}")
        return []

def main():
    for site in SITES:
        print(f"\n=== Scanning {site} ===")
        dates = list_s3_csvs(site)
        if not dates:
            print(f"[SKIP] No CSVs found for {site}")
            continue
        for d in dates:
            print(f"[IMPORT] {site} {d}")
            subprocess.run(
                ["python", "etl_from_loudness_summary.py", "--site", f"{site}_data", "--date", d],
                check=False
            )

if __name__ == "__main__":
    main()
