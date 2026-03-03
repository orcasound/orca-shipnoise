#!/usr/bin/env python3
"""
Shipnoise AIS Pipeline Orchestrator
------------------------------------
Runs continuously on fly.io as a worker process.

Two independent loops:
  1. COLLECTION: Runs AIS collection in 1-hour chunks, 24/7
  2. PROCESSING: Once per day at ~10:00 UTC (2:00 AM PST), processes
     the previous day's collected data against audio timestamps

Why 10:00 UTC?
  - Orcasound audio sessions are organized by PST (UTC-8)
  - A full PST "day" ends at 08:00 UTC the next day
  - 10:00 UTC gives a 2-hour buffer to ensure audio data is complete
  - AIS data for the UTC day is also fully collected by then

Environment variables:
  AISSTREAM_API_KEY_BUSH_POINT     — API key for bush-point
  AISSTREAM_API_KEY_ORCASOUND_LAB  — API key for orcasound-lab
  AISSTREAM_API_KEY_PORT_TOWNSEND  — API key for port-townsend
  AISSTREAM_API_KEY_SUNSET_BAY     — API key for sunset-bay
  DATABASE_URL                     — required for writing detections to Neon
  AIS_DURATION_SECS                — collection window per chunk (default: 3600)
  PROCESS_HOUR_UTC                 — hour (0-23) to trigger daily processing (default: 10)
"""

import os
import sys
import subprocess
import shutil
import time
import signal
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- Configuration ---
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
SITES_DIR = PROJECT_ROOT / "Sites"

# Hour (UTC) at which to trigger daily processing
# 10:00 UTC = 2:00 AM PST — ensures full day of audio + AIS data is available
PROCESS_HOUR_UTC = int(os.getenv("PROCESS_HOUR_UTC", "10"))

# Site → env var name mapping (one dedicated API key per site)
SITE_KEY_MAP = {
    "bush-point":    "AISSTREAM_API_KEY_BUSH_POINT",
    "orcasound-lab": "AISSTREAM_API_KEY_ORCASOUND_LAB",
    "port-townsend": "AISSTREAM_API_KEY_PORT_TOWNSEND",
    "sunset-bay":    "AISSTREAM_API_KEY_SUNSET_BAY",
}

# Site keys used by processing scripts (underscored)
PROCESS_SITES = ["bush_point", "orcasound_lab", "port_townsend", "sunset_bay"]

# Track which dates have been fully processed to avoid duplicate DB inserts
_processed_dates = set()

# Graceful shutdown
_shutdown = False


def handle_signal(signum, frame):
    global _shutdown
    print(f"\n[orchestrator] Received signal {signum}, shutting down gracefully...")
    _shutdown = True


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


def get_api_keys():
    """Load API keys from environment, one per site."""
    keys = {}
    for site, env_var in SITE_KEY_MAP.items():
        key = os.getenv(env_var)
        if key:
            keys[site] = key
            print(f"[orchestrator] Loaded {env_var} for {site}")
        else:
            print(f"[orchestrator] WARNING: {env_var} not set, skipping {site}")
    return keys


def run_cmd(args, label="", cwd=None, env=None):
    """Run a subprocess and stream its output. Returns True on success."""
    print(f"\n{'='*60}")
    print(f"[orchestrator] {label}")
    print(f"  cmd: {' '.join(str(a) for a in args)}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            args,
            cwd=cwd or str(PROJECT_ROOT),
            env=env,
            timeout=7200,  # 2-hour hard timeout
        )
        if result.returncode != 0:
            print(f"[orchestrator] WARNING: {label} exited with code {result.returncode}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"[orchestrator] ERROR: {label} timed out")
        return False
    except Exception as e:
        print(f"[orchestrator] ERROR: {label} failed: {e}")
        return False


def collect_ais(api_keys):
    """Collect AIS data for all sites in parallel, using the correct API key per site.
    Runs for AIS_DURATION_SECS (default 1 hour), then returns."""
    print("\n[orchestrator] === AIS COLLECTION ===")

    duration_secs = os.getenv("AIS_DURATION_SECS", "3600")
    try:
        duration_int = max(1, int(duration_secs))
    except ValueError:
        print(f"[orchestrator] Invalid AIS_DURATION_SECS={duration_secs!r}; falling back to 3600")
        duration_secs = "3600"
        duration_int = 3600

    procs = []
    for site, api_key in api_keys.items():
        if _shutdown:
            break

        # Each site gets its own dedicated API key
        child_env = os.environ.copy()
        child_env["AISSTREAM_API_KEY"] = api_key

        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "collect" / "ais_collect.py"),
            "--site",
            site,
            "--duration",
            duration_secs,
        ]
        print(f"[orchestrator] Starting collection for {site}")
        p = subprocess.Popen(cmd, cwd=str(PROJECT_ROOT), env=child_env)
        procs.append((site, p))
        # Stagger startup to avoid connection spikes against AIS WebSocket
        time.sleep(5)

    # Wait for all collectors to finish
    for site, p in procs:
        try:
            # Allow collectors to run for the requested duration plus a small buffer
            p.wait(timeout=duration_int + 60)
            print(f"[orchestrator] Collection done for {site} (exit={p.returncode})")
        except subprocess.TimeoutExpired:
            print(f"[orchestrator] Collection timeout for {site}, terminating")
            p.terminate()
            p.wait(timeout=10)


def get_timestamps():
    """Run preprocessing to get latest HLS timestamps from S3."""
    print("\n[orchestrator] === GET TIMESTAMPS ===")
    run_cmd(
        [sys.executable, str(SCRIPTS_DIR / "preprocess" / "get_latest_timestamp.py")],
        label="get_latest_timestamp.py",
    )


def process_pipeline(target_date_str):
    """Run the full processing pipeline for a given date."""
    print(f"\n[orchestrator] === PROCESSING PIPELINE (date={target_date_str}) ===")

    # Step 1: AIS to transits (per site)
    for site in PROCESS_SITES:
        if _shutdown:
            return
        site_slug = site.replace("_", "-")
        run_cmd(
            [sys.executable, str(SCRIPTS_DIR / "process" / "ais_to_transits.py"),
             "--site", site_slug, "--date", target_date_str],
            label=f"ais_to_transits --site {site_slug} --date {target_date_str}",
        )

    if _shutdown:
        return

    # Step 2: Match transits to audio timestamps (per site)
    for site in PROCESS_SITES:
        if _shutdown:
            return
        run_cmd(
            [sys.executable, str(SCRIPTS_DIR / "process" / "match_all_transits_to_ts.py"),
             "--site", site, "--date", target_date_str],
            label=f"match_all_transits_to_ts --site {site} --date {target_date_str}",
        )

    if _shutdown:
        return

    # Step 3: Merge and deduplicate
    run_cmd(
        [sys.executable, str(SCRIPTS_DIR / "process" / "merge_and_dedup.py"),
         "--date", target_date_str],
        label=f"merge_and_dedup --date {target_date_str}",
    )

    if _shutdown:
        return

    # Step 4: Extract loudest segments and write to DB
    run_cmd(
        [sys.executable, str(SCRIPTS_DIR / "process" / "extract_loudest_segment.py"),
         "--site", "all", "--date", target_date_str, "--verbose"],
        label=f"extract_loudest_segment --site all --date {target_date_str}",
    )


def cleanup_old_data():
    """Remove processed date folders but keep today's data (still being collected)."""
    print("\n[orchestrator] === CLEANUP ===")
    if not SITES_DIR.exists():
        return

    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    total_freed = 0

    for site_dir in SITES_DIR.iterdir():
        if not site_dir.is_dir():
            continue
        for sub in site_dir.iterdir():
            if not sub.is_dir():
                continue
            # Keep today's collection folder, delete everything else
            folder_name = sub.name
            if folder_name.isdigit() and folder_name != today_str:
                size = sum(f.stat().st_size for f in sub.rglob("*") if f.is_file())
                shutil.rmtree(sub)
                total_freed += size
                print(f"[orchestrator] Removed {site_dir.name}/{folder_name} ({size / 1024 / 1024:.1f} MB)")
            # Also clean up transits/output folders
            elif "_transits_" in folder_name or "_output" in folder_name:
                size = sum(f.stat().st_size for f in sub.rglob("*") if f.is_file())
                shutil.rmtree(sub)
                total_freed += size
                print(f"[orchestrator] Removed {site_dir.name}/{folder_name} ({size / 1024 / 1024:.1f} MB)")

    # Also clean up timestamps
    ts_dir = SITES_DIR / "timestamps"
    if ts_dir.exists():
        for sub in ts_dir.iterdir():
            if sub.is_dir() and sub.name != today_str:
                size = sum(f.stat().st_size for f in sub.rglob("*") if f.is_file())
                shutil.rmtree(sub)
                total_freed += size

    print(f"[orchestrator] Cleanup complete, freed {total_freed / 1024 / 1024:.1f} MB")


def should_process_now():
    """Check if it's time to run the daily processing pipeline.
    Triggers once per day after PROCESS_HOUR_UTC."""
    now = datetime.now(timezone.utc)
    yesterday = (now - timedelta(days=1)).strftime("%Y%m%d")

    if now.hour >= PROCESS_HOUR_UTC and yesterday not in _processed_dates:
        return yesterday
    return None


def main():
    print("[orchestrator] Shipnoise AIS Pipeline starting")
    print(f"[orchestrator] PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"[orchestrator] SITES_DIR: {SITES_DIR}")
    print(f"[orchestrator] Daily processing triggers at {PROCESS_HOUR_UTC:02d}:00 UTC")

    # Load API keys
    api_keys = get_api_keys()
    if not api_keys:
        print("[orchestrator] ERROR: No API keys configured. Set AISSTREAM_API_KEY_BUSH_POINT, AISSTREAM_API_KEY_ORCASOUND_LAB, etc.")
        sys.exit(1)

    # Ensure Sites directory exists
    SITES_DIR.mkdir(parents=True, exist_ok=True)

    cycle = 0
    while not _shutdown:
        cycle += 1
        cycle_start = datetime.now(timezone.utc)
        print(f"\n{'#'*60}")
        print(f"[orchestrator] CYCLE {cycle} at {cycle_start.isoformat()}")
        print(f"{'#'*60}")

        # --- Always: Collect AIS data (1-hour chunk) ---
        collect_ais(api_keys)

        if _shutdown:
            break

        # --- Check: Is it time for daily processing? ---
        target_date = should_process_now()
        if target_date:
            print(f"\n[orchestrator] >>> DAILY PROCESSING TRIGGERED for {target_date} <<<")

            # Get audio timestamps from S3
            get_timestamps()

            if not _shutdown:
                # Run full processing pipeline
                process_pipeline(target_date)
                _processed_dates.add(target_date)
                print(f"[orchestrator] Marked {target_date} as processed")

            if not _shutdown:
                # Clean up old data (keep today's)
                cleanup_old_data()
        else:
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
            print(f"[orchestrator] Not yet time for processing (triggers at {PROCESS_HOUR_UTC:02d}:00 UTC, yesterday={yesterday})")

        cycle_end = datetime.now(timezone.utc)
        elapsed = (cycle_end - cycle_start).total_seconds()
        print(f"\n[orchestrator] Cycle {cycle} completed in {elapsed:.0f}s")

        if not _shutdown:
            print("[orchestrator] Sleeping 30s before next collection...")
            time.sleep(30)

    print("[orchestrator] Shutdown complete")


if __name__ == "__main__":
    main()
