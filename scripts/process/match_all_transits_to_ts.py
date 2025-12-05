#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage-1: Automated AIS ↔ Hydrophone Matching (multi-site, DST-safe)
--------------------------------------------------------------------
• Automatically detects "yesterday" (UTC) as the processing date.
• Iterates through all hydrophone sites (Bush Point, Orcasound Lab, Port Townsend, Sunset Bay).
• For each site:
    - Loads timestamp files for (yesterday + previous day).
    - Loads all *_transits_filtered.csv files for the same UTC day.
    - Finds all audio .ts segments within ±3 minutes of each AIS t_cpa.
• Handles DST transitions (23h / 25h) automatically.
• Supports cross-session matching (when CPA window overlaps two sessions).
• Designed to run daily at ~00:05–00:10 UTC as a cron job or systemd timer.
"""

import argparse
import os
import pandas as pd
from datetime import datetime, timedelta, timezone

# === CONFIGURATION ===
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
SITES_DIR = os.path.join(PROJECT_ROOT, "Sites")
SITES = ["Bush_Point_data", "Orcasound_Lab_data", "Port_Townsend_data", "Sunset_Bay_data"]
GLOBAL_TS_DIR = os.path.join(SITES_DIR, "timestamps")

SITE_ALIASES = {
    "Bush_Point_data": "bush_point",
    "Orcasound_Lab_data": "orcasound_lab",
    "Port_Townsend_data": "port_townsend",
    "Sunset_Bay_data": "sunset_bay",
}

SEARCH_WINDOW = 180  # ±3 minutes
MIN_DAY_HOURS = 23.5
MAX_DAY_HOURS = 24.5


def find_timestamp_file(site_key, per_site_dir, day):
    """Find the timestamp file for a given UTC date (tolerant of naming patterns)."""
    search_dirs = []
    if per_site_dir and os.path.isdir(per_site_dir):
        search_dirs.append(per_site_dir)

    day_dir = os.path.join(GLOBAL_TS_DIR, day.strftime("%Y-%m-%d"))
    if os.path.isdir(day_dir):
        search_dirs.append(day_dir)

    if not search_dirs:
        return None

    ymd = day.strftime("%Y%m%d")
    alt = day.strftime("%Y-%m-%d")
    matches = []

    for directory in search_dirs:
        abs_dir = os.path.abspath(directory)
        is_per_site_dir = per_site_dir and abs_dir == os.path.abspath(per_site_dir)
        for name in os.listdir(directory):
            if not name.endswith("_timestamps_UTC.txt"):
                continue
            if site_key and not is_per_site_dir and site_key not in name:
                continue
            if ymd in name or alt in name:
                matches.append(os.path.join(directory, name))

    matches.sort()
    return matches[0] if matches else None


def load_timestamp_dataframe(site_key, timestamp_dir, target_date):
    """
    Load timestamp rows covering target_date.
    Includes the previous day and handles DST transitions (short/long days).
    """
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

    # If the total coverage is shorter than expected, add the next day's timestamps (DST spring forward)
    if coverage_hours < MIN_DAY_HOURS:
        next_day = target_date + timedelta(days=1)
        extra_path = find_timestamp_file(site_key, timestamp_dir, next_day)
        if extra_path:
            print(f"  ➕ DST short day detected ({coverage_hours:.2f}h). Including next-day file: {os.path.basename(extra_path)}")
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
            print(f"  ⚠️ DST short day detected ({coverage_hours:.2f}h), next-day file missing.")
    elif coverage_hours > MAX_DAY_HOURS:
        print(f"  ℹ️ DST fallback detected ({coverage_hours:.2f}h).")

    return ts_df, used_files


def process_sites(target_date, search_window):
    """Main function: match AIS CPA timestamps with audio timestamp segments."""
    utc_now = datetime.now(timezone.utc)
    print(f"🕒 UTC now: {utc_now}")
    print(f"🎯 Target AIS date: {target_date}")

    window = timedelta(seconds=search_window)

    for site in SITES:
        base_dir = os.path.join(SITES_DIR, site)
        timestamp_dir = os.path.join(base_dir, "timestamps")

        if not os.path.isdir(base_dir):
            print(f"⚠️ Site directory missing: {base_dir}")
            continue

        print(f"\n🌊 Processing site: {site}")
        target_folder = os.path.join(base_dir, f"{target_date.strftime('%Y%m%d')}_transits_filtered")
        if not os.path.isdir(target_folder):
            print(f"  ⚠️ No folder for {target_date} — skipping.")
            continue

        csv_files = [f for f in os.listdir(target_folder) if f.endswith("_transits_filtered.csv")]
        if not csv_files:
            print(f"  ⚠️ No AIS files found for {target_date} — skipping.")
            continue

        site_key = SITE_ALIASES.get(site, site.lower())
        ts_df, file_info = load_timestamp_dataframe(site_key, timestamp_dir, target_date)
        if ts_df is None or ts_df.empty:
            print("  ❌ No timestamp files available — skipping site.")
            continue

        for label, name in file_info:
            print(f"  ✅ Using {label} timestamp file: {name}")

        print(f"  📈 Loaded {len(ts_df)} timestamp segments")
        print("     Time coverage:", ts_df['start'].min(), "→", ts_df['end'].max())

        duration_hours = (ts_df["end"].max() - ts_df["start"].min()).total_seconds() / 3600
        if duration_hours > MAX_DAY_HOURS:
            print("  ⚠️ DST fallback detected (~25h recording window).")
        elif duration_hours < MIN_DAY_HOURS:
            print("  ⚠️ DST start detected (~23h recording window).")
        else:
            print("  ✅ Normal ~24h recording window.")

        # === MATCH EACH AIS FILE ===
        for csv_name in csv_files:
            in_path = os.path.join(target_folder, csv_name)
            out_path = in_path.replace("_filtered.csv", "_windowed.csv")

            print(f"  🔍 Matching AIS file: {csv_name}")
            df = pd.read_csv(in_path, parse_dates=["t_cpa"])
            output_rows = []

            for _, row in df.iterrows():
                t_cpa = row["t_cpa"]

                # Select timestamp rows that overlap the CPA ± search_window
                subset = ts_df[
                    (ts_df["end"] >= t_cpa - window) &
                    (ts_df["start"] <= t_cpa + window)
                ]

                out = row.to_dict()
                if subset.empty:
                    out.update({
                        "match_status": "no_segments",
                        "segment_count": 0,
                        "segment_range": None
                    })
                else:
                    # === Multi-session support ===
                    files = subset["file"].tolist()
                    parts = [f.split("/")[-2:] for f in files if "/" in f]

                    # Group by session ID (the parent folder name)
                    session_map = {}
                    for session, name in parts:
                        if not (name.startswith("live") and name.endswith(".ts")):
                            continue
                        try:
                            num = int(name.replace("live", "").replace(".ts", ""))
                            session_map.setdefault(session, []).append(num)
                        except ValueError:
                            continue

                    if not session_map:
                        segment_range = None
                    else:
                        ranges = []
                        for session, nums in sorted(session_map.items()):
                            low, high = min(nums), max(nums)
                            ranges.append(f"{session}/live{low}-live{high}")
                        segment_range = ", ".join(ranges)

                    out.update({
                        "match_status": "window_found",
                        "segment_count": len(files),
                        "segment_range": segment_range
                    })

                output_rows.append(out)

            out_df = pd.DataFrame(output_rows)
            out_df.to_csv(out_path, index=False)
            print(f"    ✅ Saved {len(out_df)} rows → {out_path}")

    print("\n🎉 Stage-1 complete for all sites (automated UTC daily run).")
    print("   Next: Stage-2 loudness extraction.")


def parse_args():
    parser = argparse.ArgumentParser(description="Match AIS transits with audio timestamps.")
    parser.add_argument("--date", help="UTC date (YYYYMMDD) to process; default is yesterday.")
    parser.add_argument("--search-window", type=int, default=SEARCH_WINDOW,
                        help="Half-window size in seconds for segment search (default: 180).")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y%m%d").date()
        except ValueError:
            raise SystemExit(f"Invalid --date value: {args.date}. Expected YYYYMMDD.")
    else:
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    process_sites(target_date, args.search_window)
