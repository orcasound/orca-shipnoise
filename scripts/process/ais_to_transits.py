#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import math
import os
import glob
import sys
import pandas as pd
from datetime import datetime, timezone, timedelta

# === Constants ===
RADIUS_M = 30000
CPA_MAX_M = 20000
MIN_SOG_KT = 2
MIN_POINTS = 3
MIN_DWELL_SEC = 60
HIGH_QUALITY_THRESHOLD = 1000

# === Project root ===
def find_project_root(start_path):
    cur = os.path.abspath(start_path)
    for _ in range(6):
        if os.path.isdir(os.path.join(cur, "Sites")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    raise RuntimeError("Cannot locate project root containing 'Sites'")

PROJECT_ROOT = find_project_root(os.path.dirname(__file__))

# === CLI ===
def parse_args():
    p = argparse.ArgumentParser(description="Filter AIS transits for a site")
    p.add_argument("--site", required=True, help="Site slug, e.g. bush-point")
    p.add_argument("--date", help="UTC date YYYYMMDD (default: yesterday)")
    p.add_argument("--all", action="store_true", help="Process all available dates")
    return p.parse_args()

# === Geometry ===
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def compute_bearing(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

# === Time ===
def parse_time(ts_str):
    if not ts_str:
        return None
    ts_str = ts_str.replace(" UTC", "").replace("+0000", "").strip()
    if "." in ts_str:
        prefix, rest = ts_str.split(".", 1)
        subsec = "".join(ch for ch in rest if ch.isdigit())[:6]
        ts_str = f"{prefix}.{subsec}"
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts_str, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None

def to_utc_iso(dt):
    if not isinstance(dt, datetime) or pd.isna(dt):
        return ""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# === Static cache ===
def load_static_cache(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_static_cache(path, cache):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

# === Meta ===
def read_meta(infile):
    with open(infile, "r", encoding="utf-8") as f:
        first = f.readline()
    try:
        obj = json.loads(first)
        return obj.get("_meta", {})
    except Exception:
        return {}

# === Core processing ===
def process_file(infile, outfile, static_cache, hydro_lat, hydro_lon, site_name):
    records = []
    with open(infile, "r", encoding="utf-8", errors="ignore") as f:
        _ = f.readline()
        for line in f:
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
            except Exception:
                continue

            mtype = msg.get("MessageType")
            meta = msg.get("MetaData", {})

            if mtype == "ShipStaticData":
                mmsi = meta.get("MMSI")
                if not mmsi:
                    continue
                data = msg.get("Message", {}).get("ShipStaticData", {})
                dim = data.get("Dimension", {}) or {}
                length = (dim.get("A") or 0) + (dim.get("B") or 0) or None
                width = (dim.get("C") or 0) + (dim.get("D") or 0) or None
                static_cache[str(mmsi)] = {
                    "name": (data.get("Name") or "").strip(),
                    "type": data.get("Type"),
                    "draught": data.get("MaximumStaticDraught"),
                    "length_m": length,
                    "width_m": width,
                }
                continue

            if mtype != "PositionReport":
                continue

            lat = meta.get("latitude")
            lon = meta.get("longitude")
            t = parse_time(meta.get("time_utc"))
            if lat is None or lon is None or t is None:
                continue

            dist = haversine(hydro_lat, hydro_lon, lat, lon)
            m = msg.get("Message", {}).get("PositionReport", {})
            mmsi = str(meta.get("MMSI"))
            ship_info = static_cache.get(mmsi, {})

            records.append({
                "mmsi": mmsi,
                "shipname": meta.get("ShipName") or ship_info.get("name", ""),
                "shiptype": ship_info.get("type", ""),
                "draught": ship_info.get("draught"),
                "length_m": ship_info.get("length_m"),
                "width_m": ship_info.get("width_m"),
                "time": t,
                "lat": lat,
                "lon": lon,
                "sog": m.get("Sog"),
                "cog": m.get("Cog"),
                "heading": m.get("TrueHeading"),
                "dist_m": dist
            })

    df = pd.DataFrame(records)
    if df.empty:
        return

    transits = []
    for mmsi, g in df.groupby("mmsi"):
        inside = g[g["dist_m"] <= RADIUS_M]
        if inside.empty:
            continue
        inside = inside[(inside["sog"].isna()) | (inside["sog"] >= MIN_SOG_KT)]
        if len(inside) < MIN_POINTS:
            continue

        dwell = (inside["time"].iloc[-1] - inside["time"].iloc[0]).total_seconds()
        if dwell < MIN_DWELL_SEC:
            continue

        cpa_row = inside.loc[inside["dist_m"].idxmin()]
        if cpa_row["dist_m"] > CPA_MAX_M:
            continue

        t_entry, t_exit = inside["time"].iloc[0], inside["time"].iloc[-1]
        quality_tag = "high-quality" if cpa_row["dist_m"] < HIGH_QUALITY_THRESHOLD else "normal"
        bearing = compute_bearing(hydro_lat, hydro_lon, cpa_row["lat"], cpa_row["lon"])

        transits.append({
            "mmsi": mmsi,
            "shipname": cpa_row["shipname"],
            "shiptype": cpa_row["shiptype"],
            "draught": cpa_row["draught"],
            "length_m": cpa_row["length_m"],
            "width_m": cpa_row["width_m"],
            "t_entry": to_utc_iso(t_entry),
            "t_cpa": to_utc_iso(cpa_row["time"]),
            "t_exit": to_utc_iso(t_exit),
            "transit_duration_min": round((t_exit - t_entry).total_seconds() / 60, 2),
            "cpa_distance_m": round(cpa_row["dist_m"], 1),
            "relative_bearing_deg": round(bearing, 1),
            "quality_tag": quality_tag,
            "site_name": site_name
        })

    if transits:
        os.makedirs(os.path.dirname(outfile), exist_ok=True)
        pd.DataFrame(transits).to_csv(outfile, index=False)

# === Main ===
def main():
    args = parse_args()
    site = args.site
    slug = site.replace("-", "_").lower()

    sites_root = os.path.join(PROJECT_ROOT, "Sites")
    base_dir = None
    for name in os.listdir(sites_root):
        if not name.lower().endswith("_data"):
            continue
        if name.lower().replace("_data", "") == slug:
            base_dir = os.path.join(sites_root, name)
            break

    if not base_dir:
        print(f"❌ No site folder found for {site}")
        sys.exit(1)

    static_cache_path = os.path.join(base_dir, "static_cache.json")
    static_cache = load_static_cache(static_cache_path)

    available = sorted([
        d for d in os.listdir(base_dir)
        if d.isdigit() and os.path.isdir(os.path.join(base_dir, d))
    ])

    if not available:
        print("⚠️ No date folders found.")
        return

    if args.all:
        targets = available
    else:
        target = args.date or (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
        if target not in available:
            print(f"⚠️ Requested date {target} not found.")
            return
        targets = [target]

    print(f"🎯 Processing site={site}, dates={targets}")

    for d in targets:
        folder = os.path.join(base_dir, d)
        out_folder = f"{folder}_transits_filtered"
        os.makedirs(out_folder, exist_ok=True)

        for infile in sorted(glob.glob(os.path.join(folder, "ais_raw_*.jsonl"))):
            meta = read_meta(infile)
            hydro_lat = meta.get("latitude")
            hydro_lon = meta.get("longitude")
            site_name = meta.get("site", site)

            if hydro_lat is None or hydro_lon is None:
                print(f"⚠️ Missing meta in {infile}, skipping.")
                continue

            outfile = os.path.join(out_folder, os.path.basename(infile).replace(".jsonl", "_transits_filtered.csv"))
            process_file(infile, outfile, static_cache, hydro_lat, hydro_lon, site_name)

    save_static_cache(static_cache_path, static_cache)

if __name__ == "__main__":
    main()
