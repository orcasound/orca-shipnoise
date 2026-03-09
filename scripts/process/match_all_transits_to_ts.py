#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage-1: Automated AIS ↔ Hydrophone Matching (multi-site, DST-safe)
--------------------------------------------------------------------
• Default: process all sites.
• Supports --site <slug> to process a single site.
• Supports --date YYYYMMDD (UTC).
• Supports timestamps directory in both YYYY-MM-DD and YYYYMMDD formats.
"""

import argparse
import os
import sys
import pandas as pd
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from sites import KEY_TO_DATA_DIR

# === CONFIGURATION ===
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
SITES_DIR = os.path.join(PROJECT_ROOT, "Sites")
GLOBAL_TS_DIR = os.path.join(SITES_DIR, "timestamps")

SITES = KEY_TO_DATA_DIR

SEARCH_WINDOW = 180  # ±3 minutes
MIN_DAY_HOURS = 23.5
MAX_DAY_HOURS = 24.5


# ---------- Timestamp helpers ----------

def find_timestamp_file(site_key, per_site_dir, day):
    """Find the timestamp file for a given UTC date (supports YYYY-MM-DD and YYYYMMDD)."""
    search_dirs = []
    if per_site_dir and os.path.isdir(per_site_dir):
        search_dirs.append(per_site_dir)

    day_compact = os.path.join(GLOBAL_TS_DIR, day.strftime("%Y%m%d"))
    if os.path.isdir(day_compact):
        search_dirs.append(day_compact)

    if not search_dirs:
        return None

    ymd = day.strftime("%Y%m%d")
    matches = []

    for directory in search_dirs:
        for name in os.listdir(directory):
            if not name.endswith("_timestamps_UTC.txt"):
                continue
            if site_key and site_key not in name:
                continue
            if ymd in name:
                matches.append(os.path.join(directory, name))

    matches.sort()
    return matches[0] if matches else None


def load_timestamp_dataframe(site_key, timestamp_dir, target_date):
    requested = [
        (target_date - timedelta(days=1), "previous"),
        (target_date, "target"),
    ]

    ts_frames = []
    used_files = []

    for day, label in requested:
        fpath = find_timestamp_file(site_key, timestamp_dir, day)
        if not fpath:
            continue
        try:
            df = pd.read_csv(
                fpath,
                names=["file", "start", "end"],
                parse_dates=["start", "end"]
            )
            ts_frames.append(df)
            used_files.append((label, os.path.basename(fpath)))
        except Exception as exc:
            print(f"  ❌ Failed to read timestamp file {fpath}: {exc}")

    if not ts_frames:
        return None, used_files

    ts_df = pd.concat(ts_frames, ignore_index=True)
    ts_df = ts_df.drop_duplicates(subset=["file"]).sort_values("start")

    if ts_df.empty:
        return None, used_files

    coverage_hours = (ts_df["end"].max() - ts_df["start"].min()).total_seconds() / 3600

    if coverage_hours < MIN_DAY_HOURS:
        next_day = target_date + timedelta(days=1)
        extra_path = find_timestamp_file(site_key, timestamp_dir, next_day)
        if extra_path:
            print(f"  ➕ DST short day detected ({coverage_hours:.2f}h). Including next-day file.")
            try:
                extra_df = pd.read_csv(
                    extra_path,
                    names=["file", "start", "end"],
                    parse_dates=["start", "end"]
                )
                ts_df = pd.concat([ts_df, extra_df], ignore_index=True)
                ts_df = ts_df.drop_duplicates(subset=["file"]).sort_values("start")
                used_files.append(("next-day", os.path.basename(extra_path)))
            except Exception as exc:
                print(f"  ❌ Failed to read next-day timestamp file {extra_path}: {exc}")
        else:
            print(f"  ⚠️ DST short day detected, next-day file missing.")
    elif coverage_hours > MAX_DAY_HOURS:
        print(f"  ℹ️ DST fallback detected ({coverage_hours:.2f}h).")

    return ts_df, used_files


# ---------- Core ----------

def process_sites(target_date, search_window, only_site=None):
    utc_now = datetime.now(timezone.utc)
    print(f"🕒 UTC now: {utc_now}")
    print(f"🎯 Target AIS date: {target_date}")

    window = timedelta(seconds=search_window)

    for site_key, folder_name in SITES.items():
        if only_site and site_key != only_site:
            continue

        base_dir = os.path.join(SITES_DIR, folder_name)
        timestamp_dir = os.path.join(base_dir, "timestamps")

        if not os.path.isdir(base_dir):
            print(f"⚠️ Site directory missing: {base_dir}")
            continue

        print(f"\n🌊 Processing site: {site_key}")
        target_folder = os.path.join(base_dir, f"{target_date.strftime('%Y%m%d')}_transits_filtered")
        if not os.path.isdir(target_folder):
            print(f"  ⚠️ No folder for {target_date} — skipping.")
            continue

        csv_files = [f for f in os.listdir(target_folder) if f.endswith("_transits_filtered.csv")]
        if not csv_files:
            print(f"  ⚠️ No AIS files found — skipping.")
            continue

        ts_df, file_info = load_timestamp_dataframe(site_key, timestamp_dir, target_date)
        if ts_df is None or ts_df.empty:
            print("  ❌ No timestamp files available — skipping site.")
            continue

        for label, name in file_info:
            print(f"  ✅ Using {label} timestamp file: {name}")

        print(f"  📈 Loaded {len(ts_df)} timestamp segments")
        print("     Time coverage:", ts_df['start'].min(), "→", ts_df['end'].max())

        for csv_name in csv_files:
            in_path = os.path.join(target_folder, csv_name)
            out_path = in_path.replace("_filtered.csv", "_windowed.csv")

            print(f"  🔍 Matching AIS file: {csv_name}")
            df = pd.read_csv(in_path, parse_dates=["t_cpa"])
            output_rows = []

            for _, row in df.iterrows():
                t_cpa = row["t_cpa"]

                subset = ts_df[
                    (ts_df["end"] >= t_cpa - window) &
                    (ts_df["start"] <= t_cpa + window)
                ]

                out = row.to_dict()
                if subset.empty:
                    out.update({"match_status": "no_segments", "segment_count": 0, "segment_range": None})
                else:
                    files = subset["file"].tolist()
                    parts = [f.split("/")[-2:] for f in files if "/" in f]

                    session_map = {}
                    for session, name in parts:
                        if name.startswith("live") and name.endswith(".ts"):
                            try:
                                num = int(name.replace("live", "").replace(".ts", ""))
                                session_map.setdefault(session, []).append(num)
                            except ValueError:
                                pass

                    ranges = []
                    for session, nums in sorted(session_map.items()):
                        ranges.append(f"{session}/live{min(nums)}-live{max(nums)}")

                    out.update({
                        "match_status": "window_found",
                        "segment_count": len(files),
                        "segment_range": ", ".join(ranges) if ranges else None
                    })

                output_rows.append(out)

            out_df = pd.DataFrame(output_rows)
            out_df.to_csv(out_path, index=False)
            print(f"    ✅ Saved {len(out_df)} rows → {out_path}")

    print("\n🎉 Stage-1 complete.")


# ---------- CLI ----------

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="UTC date YYYYMMDD (default: yesterday)")
    parser.add_argument("--search-window", type=int, default=SEARCH_WINDOW)
    parser.add_argument("--site", help="Only process one site (bush_point, orcasound_lab, etc.)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y%m%d").date()
        except ValueError:
            raise SystemExit("Invalid --date format, expected YYYYMMDD.")
    else:
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    process_sites(target_date, args.search_window, args.site)
