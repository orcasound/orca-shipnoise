#!/usr/bin/env python3
"""
Analyze historical AIS .jsonl files to compute per-site message count baseline.
Prints mean, median, min, max, and stddev of messages per hour for each site.
"""
import json
from pathlib import Path
from collections import defaultdict
import statistics

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SITES_DIR = PROJECT_ROOT / "Sites"


def count_messages(path: Path) -> int:
    """Count AIS messages in a .jsonl file (total lines minus the _meta header)."""
    total = 0
    with open(path, encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            if i == 0:
                continue  # skip _meta
            if line.strip():
                total += 1
    return total


def main():
    site_counts: dict[str, list[int]] = defaultdict(list)
    skipped = 0

    for jsonl in sorted(SITES_DIR.rglob("ais_raw_*.jsonl")):
        # e.g. Sites/bush_point_data/20260306/ais_raw_...jsonl
        site_dir = jsonl.parts[-3]  # bush_point_data
        site = site_dir.replace("_data", "")
        n = count_messages(jsonl)
        if n == 0:
            skipped += 1
            continue  # skip empty files (failed/interrupted collections)
        site_counts[site].append(n)
        print(f"  {site:20s}  {jsonl.parts[-2]}  {jsonl.name}  → {n} msgs")

    print(f"\n(skipped {skipped} empty files)\n")

    print()
    print(f"{'site':<22} {'files':>5} {'mean':>7} {'median':>7} {'min':>6} {'max':>6} {'stdev':>7}")
    print("-" * 62)
    for site, counts in sorted(site_counts.items()):
        mean   = statistics.mean(counts)
        median = statistics.median(counts)
        lo     = min(counts)
        hi     = max(counts)
        stdev  = statistics.stdev(counts) if len(counts) > 1 else 0.0
        print(f"{site:<22} {len(counts):>5} {mean:>7.0f} {median:>7.0f} {lo:>6} {hi:>6} {stdev:>7.1f}")

    print()
    print("Suggested anomaly threshold: mean - 2*stdev (flag if below this)")
    print()
    for site, counts in sorted(site_counts.items()):
        if len(counts) < 2:
            print(f"  {site}: only {len(counts)} file(s), need more data for a reliable threshold")
            continue
        mean  = statistics.mean(counts)
        stdev = statistics.stdev(counts)
        threshold = max(0, mean - 2 * stdev)
        print(f"  {site}: threshold ≈ {threshold:.0f} msgs/hour  (mean={mean:.0f}, stdev={stdev:.1f})")


if __name__ == "__main__":
    main()
