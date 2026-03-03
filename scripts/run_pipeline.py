#!/usr/bin/env python3
"""
Shipnoise AIS Pipeline Orchestrator
------------------------------------
Runs continuously on fly.io as a worker process:
  1. Collects AIS data for all sites in parallel (default: 1 hour per cycle)
  2. Runs the processing pipeline on yesterday's data
  3. Loops back to collection

Environment variables:
  AISSTREAM_API_KEY  — required for AIS collection
  DATABASE_URL       — required for writing detections to Neon
  AIS_DURATION_SECS  — collection window per cycle (default: 3600)
"""

import os
import sys
import subprocess
import time
import signal
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- Configuration ---
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
SITES_DIR = PROJECT_ROOT / "Sites"

# Site slugs used by ais_collect.py (hyphenated)
COLLECT_SITES = ["bush-point", "orcasound-lab", "port-townsend", "sunset-bay"]

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


def run_cmd(args, label="", cwd=None):
    """Run a subprocess and stream its output. Returns True on success."""
    print(f"\n{'='*60}")
    print(f"[orchestrator] {label}")
    print(f"  cmd: {' '.join(str(a) for a in args)}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            args,
            cwd=cwd or str(PROJECT_ROOT),
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


def collect_ais():
    """Collect AIS data for all sites in parallel."""
    print("\n[orchestrator] === PHASE 1: AIS COLLECTION ===")

    procs = []
    for site in COLLECT_SITES:
        if _shutdown:
            break
        cmd = [sys.executable, str(SCRIPTS_DIR / "collect" / "ais_collect.py"), "--site", site]
        print(f"[orchestrator] Starting collection for {site}")
        p = subprocess.Popen(cmd, cwd=str(PROJECT_ROOT))
        procs.append((site, p))

    # Wait for all collectors to finish
    for site, p in procs:
        try:
            p.wait(timeout=7200)
            print(f"[orchestrator] Collection done for {site} (exit={p.returncode})")
        except subprocess.TimeoutExpired:
            print(f"[orchestrator] Collection timeout for {site}, terminating")
            p.terminate()
            p.wait(timeout=10)


def get_timestamps():
    """Run preprocessing to get latest HLS timestamps from S3."""
    print("\n[orchestrator] === PHASE 2: GET TIMESTAMPS ===")
    run_cmd(
        [sys.executable, str(SCRIPTS_DIR / "preprocess" / "get_latest_timestamp.py")],
        label="get_latest_timestamp.py",
    )


def process_pipeline(target_date_str):
    """Run the full processing pipeline for a given date."""
    print(f"\n[orchestrator] === PHASE 3: PROCESSING PIPELINE (date={target_date_str}) ===")

    # Step 1: AIS to transits (per site)
    for site in PROCESS_SITES:
        if _shutdown:
            return
        # Use hyphenated slug for ais_to_transits
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


def main():
    print("[orchestrator] Shipnoise AIS Pipeline starting")
    print(f"[orchestrator] PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"[orchestrator] SITES_DIR: {SITES_DIR}")

    # Ensure Sites directory exists
    SITES_DIR.mkdir(parents=True, exist_ok=True)

    cycle = 0
    while not _shutdown:
        cycle += 1
        cycle_start = datetime.now(timezone.utc)
        print(f"\n{'#'*60}")
        print(f"[orchestrator] CYCLE {cycle} started at {cycle_start.isoformat()}")
        print(f"{'#'*60}")

        # Phase 1: Collect AIS data (runs for AIS_DURATION_SECS, default 1 hour)
        collect_ais()

        if _shutdown:
            break

        # Phase 2: Get latest timestamps from S3
        get_timestamps()

        if _shutdown:
            break

        # Phase 3: Process yesterday's data (if not already done)
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
        if yesterday not in _processed_dates:
            process_pipeline(yesterday)
            _processed_dates.add(yesterday)
            print(f"[orchestrator] Marked {yesterday} as processed")
        else:
            print(f"[orchestrator] Date {yesterday} already processed, skipping pipeline")

        cycle_end = datetime.now(timezone.utc)
        elapsed = (cycle_end - cycle_start).total_seconds()
        print(f"\n[orchestrator] Cycle {cycle} completed in {elapsed:.0f}s")

        if not _shutdown:
            print("[orchestrator] Sleeping 30s before next cycle...")
            time.sleep(30)

    print("[orchestrator] Shutdown complete")


if __name__ == "__main__":
    main()
