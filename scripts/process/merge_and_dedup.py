#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage-2A: merge_and_dedup_all_sites.py (multi-site, acoustic relevance)
-----------------------------------------------------------------------
• Processes *all* daily folders for every hydrophone site under Sites/.
• For each {DATE}_transits_filtered/ folder:
    1. Merge all *_windowed.csv files.
    2. Filter out vessels too far to be acoustically relevant.
    3. Deduplicate by MMSI (keep the nearest CPA distance).
    4. Save to {DATE}_output/{DATE}_windowed_merged.csv.
"""

import argparse
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

from config.sites import KEY_TO_DATA_DIR, CPA_OVERRIDES, DEFAULT_CPA_MAX_M, LARGE_SHIP_CPA_MAX_M, SMALL_SHIP_CPA_MAX_M, LARGE_SHIP_MIN_M, SMALL_SHIP_MAX_M

# ===== CONFIGURATION =====
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
SITES_DIR = os.path.join(PROJECT_ROOT, "Sites")
SITES = list(KEY_TO_DATA_DIR.values())


def is_acoustically_relevant(row):
    """Return True if vessel is within plausible acoustic detection range."""
    cpa = row.get("cpa_distance_m", np.nan)
    length = row.get("length_m", np.nan)
    site_raw = str(row.get("site_name", "")).strip()
    site_key = site_raw.replace("-", "_").lower().removesuffix("_data") if site_raw else None
    limits = CPA_OVERRIDES.get(site_key, {})
    default_max = limits.get("default", DEFAULT_CPA_MAX_M)
    large_max = limits.get("large", LARGE_SHIP_CPA_MAX_M)
    small_max = limits.get("small", SMALL_SHIP_CPA_MAX_M)

    if pd.isna(cpa):
        return False
    if not pd.isna(length):
        if length > LARGE_SHIP_MIN_M:
            return cpa <= large_max
        elif length < SMALL_SHIP_MAX_M:
            return cpa <= small_max
    return cpa <= default_max


def process_day_folder(site_dir, date_folder):
    """Process one site-day folder."""
    date_str = date_folder.replace("_transits_filtered", "")
    input_dir = os.path.join(site_dir, date_folder)
    output_dir = os.path.join(site_dir, f"{date_str}_output")
    os.makedirs(output_dir, exist_ok=True)

    output_csv = os.path.join(output_dir, f"{date_str}_windowed_merged.csv")

    # Collect all *_windowed.csv files
    windowed_files = [
        os.path.join(input_dir, f)
        for f in os.listdir(input_dir)
        if f.endswith("_windowed.csv")
    ]
    if not windowed_files:
        print(f"⚠️ No _windowed.csv files found in {input_dir}")
        return

    print(f"\n📂 Processing {date_folder} ({len(windowed_files)} files)")

    df_list = []
    for f in sorted(windowed_files):
        try:
            tmp = pd.read_csv(f)
            df_list.append(tmp)
            print(f"  + Loaded {os.path.basename(f)} ({len(tmp)} rows)")
        except Exception as e:
            print(f"⚠️ Failed to read {f}: {e}")

    df = pd.concat(df_list, ignore_index=True)
    print(f"📊 Combined total rows: {len(df)}")

    # Verify required columns
    required = ["mmsi", "t_cpa", "segment_range"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # ===== Acoustic Relevance Filter =====
    if "cpa_distance_m" in df.columns:
        before = len(df)
        df = df[df.apply(is_acoustically_relevant, axis=1)]
        after = len(df)
        print(f"🎧 Filtered by CPA distance: {before} → {after} acoustically relevant vessels")
    else:
        print("⚠️ Column 'cpa_distance_m' not found — skipped distance filter")

    # ===== Sort & Deduplicate =====
    df["t_cpa"] = pd.to_datetime(df["t_cpa"], errors="coerce")
    df = df.sort_values("cpa_distance_m").drop_duplicates(subset=["mmsi"], keep="first")

    print(f"✅ Unique vessels after deduplication: {len(df)}")

    df.to_csv(output_csv, index=False)
    print(f"💾 Saved merged CSV → {output_csv}")


def process_site(site_name, target_dates=None):
    """Process all day folders for one site."""
    site_dir = os.path.join(SITES_DIR, site_name)
    if not os.path.isdir(site_dir):
        print(f"⚠️ Site directory not found: {site_dir}")
        return

    if target_dates:
        expected = [f"{d}_transits_filtered" for d in target_dates]
        day_folders = [
            f for f in expected
            if os.path.isdir(os.path.join(site_dir, f))
        ]
        missing = sorted(set(expected) - set(day_folders))
        for miss in missing:
            print(f"  ⚠️ Missing folder for target date: {site_name}/{miss}")
    else:
        day_folders = [
            f for f in os.listdir(site_dir)
            if f.endswith("_transits_filtered") and os.path.isdir(os.path.join(site_dir, f))
        ]

    if not day_folders:
        print(f"⚠️ No *_transits_filtered folders found for {site_name}")
        return

    print(f"\n🌊 Site: {site_name} — Processing {len(day_folders)} folder(s)")
    for folder in sorted(day_folders):
        process_day_folder(site_dir, folder)


def parse_args():
    parser = argparse.ArgumentParser(description="Merge and deduplicate matched AIS transits.")
    parser.add_argument("--date", help="UTC date (YYYYMMDD) to process; default is yesterday.")
    parser.add_argument("--all", action="store_true", help="Process every available date folder.")
    return parser.parse_args()


def resolve_targets(available_folders, args):
    if args.all:
        return sorted({f.split("_")[0] for f in available_folders})

    target = args.date
    if not target:
        target = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
    return [target]


def main():
    args = parse_args()
    print(f"📁 Scanning all sites under: {SITES_DIR}")
    all_day_folders = []
    for site in SITES:
        site_dir = os.path.join(SITES_DIR, site)
        if not os.path.isdir(site_dir):
            continue
        for f in os.listdir(site_dir):
            if f.endswith("_transits_filtered") and os.path.isdir(os.path.join(site_dir, f)):
                all_day_folders.append(f)

    targets = resolve_targets(all_day_folders, args)
    print(f"🎯 Target dates: {', '.join(targets)}")

    for site in SITES:
        process_site(site, targets if not args.all else None)
    print("\n🎉 Stage-2A complete for all sites.")


# ===== ENTRY POINT =====
if __name__ == "__main__":
    main()
