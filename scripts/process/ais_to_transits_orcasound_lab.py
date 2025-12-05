#!/usr/bin/env python3
"""
AIS → Transits Acoustic Filter (Orcasound Lab)
---------------------------------------------
Collect AIS within 30 km radius, filter acoustically relevant transits
(CPA ≤ 3 km, min dwell 60 s, min 3 AIS points).
Adds relative bearing, site name, and high-quality tag.
Automatically locates /Sites/Orcasound_Lab_data from any script location.
"""

import argparse
import json
import math
import os
import glob
import sys
import pandas as pd
from datetime import datetime, timezone, timedelta

# === CONFIGURATION ===
HYDRO_LAT, HYDRO_LON = 48.5583362, -123.1735774  # Orcasound Lab hydrophone
SITE_NAME = "Orcasound_Lab"

RADIUS_M = 30000                 # Subscription radius (30 km)
CPA_MAX_M = 3000                 # Acoustic relevance threshold (3 km)
MIN_SOG_KT = 5.0                 # Minimum vessel speed (knots)
MIN_POINTS = 3                   # Minimum number of AIS points inside radius
MIN_DWELL_SEC = 60               # Minimum dwell time (seconds)
HIGH_QUALITY_THRESHOLD = 500     # "high-quality" if CPA < 500 m


# --- Project root / BASE_DIR locator ---
def find_project_root(start_path):
    cur = os.path.abspath(start_path)
    for _ in range(6):
        sites_dir = os.path.join(cur, "Sites")
        if os.path.isdir(sites_dir):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    raise RuntimeError("Cannot locate project root containing 'Sites'")


PROJECT_ROOT = find_project_root(os.path.dirname(__file__))
BASE_DIR = os.path.join(PROJECT_ROOT, "Sites", f"{SITE_NAME}_data")
STATIC_CACHE_PATH = os.path.join(BASE_DIR, "static_cache.json")

print(f"[PATH] PROJECT_ROOT = {PROJECT_ROOT}")
print(f"[PATH] BASE_DIR     = {BASE_DIR}")


# === Haversine distance (meters) ===
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# === Bearing (degrees clockwise from North) ===
def compute_bearing(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


# === Parse AIS timestamp safely ===
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


# === Convert datetime to ISO UTC ===
def to_utc_iso(dt):
    if not isinstance(dt, datetime) or pd.isna(dt):
        return ""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# === Load / Save static cache ===
def load_static_cache():
    if os.path.exists(STATIC_CACHE_PATH):
        try:
            with open(STATIC_CACHE_PATH, "r", encoding="utf-8") as f:
                cache = json.load(f)
            print(f"Loaded static cache with {len(cache)} ships")
            return cache
        except Exception:
            print("⚠️ Failed to read static cache, starting empty.")
    return {}


def save_static_cache(cache):
    os.makedirs(os.path.dirname(STATIC_CACHE_PATH), exist_ok=True)
    with open(STATIC_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)
    print(f"Saved static cache with {len(cache)} ships")


# === Helpers to compute ship length/width from AIS dimensions ===
def compute_length_width(dim):
    if not isinstance(dim, dict):
        return None, None
    a = dim.get("A", 0) or 0
    b = dim.get("B", 0) or 0
    c = dim.get("C", 0) or 0
    d = dim.get("D", 0) or 0
    length = a + b if (a or b) else None
    width = c + d if (c or d) else None
    return length, width


# === Process one AIS file ===
def process_file(infile, outfile, static_cache):
    records = []
    cnt_position = cnt_static = cnt_other = cnt_decode_err = 0

    with open(infile, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
            except Exception:
                cnt_decode_err += 1
                continue

            mtype = msg.get("MessageType")
            meta = msg.get("MetaData", {})

            if mtype == "ShipStaticData":
                cnt_static += 1
                mmsi = meta.get("MMSI")
                if not mmsi:
                    continue
                data = msg.get("Message", {}).get("ShipStaticData", {})
                length_m, width_m = compute_length_width(data.get("Dimension", {}))
                static_cache[str(mmsi)] = {
                    "name": (data.get("Name") or "").strip(),
                    "imo": data.get("ImoNumber"),
                    "type": data.get("Type"),
                    "draught": data.get("MaximumStaticDraught"),
                    "length_m": length_m,
                    "width_m": width_m,
                }
                continue

            if mtype != "PositionReport":
                cnt_other += 1
                continue

            cnt_position += 1
            lat = meta.get("latitude")
            lon = meta.get("longitude")
            t = parse_time(meta.get("time_utc"))
            if lat is None or lon is None or t is None:
                continue

            dist = haversine(HYDRO_LAT, HYDRO_LON, lat, lon)
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

    print(f"\n[DEBUG] {os.path.basename(infile)}:")
    print(f"  PositionReport = {cnt_position}")
    print(f"  ShipStaticData = {cnt_static}")
    print(f"  Other messages = {cnt_other}")
    print(f"  JSON decode errors = {cnt_decode_err}")

    df = pd.DataFrame(records)
    if df.empty:
        print(f"⚠️ No valid PositionReports found in {infile}")
        return

    transits = []
    for mmsi, group in df.groupby("mmsi"):
        g = group.sort_values("time")
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

        t_entry = inside["time"].iloc[0]
        t_exit = inside["time"].iloc[-1]
        quality_tag = "high-quality" if cpa_row["dist_m"] < HIGH_QUALITY_THRESHOLD else "normal"
        bearing = compute_bearing(HYDRO_LAT, HYDRO_LON, cpa_row["lat"], cpa_row["lon"])

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
            "sog_at_cpa": cpa_row["sog"],
            "cog_at_cpa": cpa_row["cog"],
            "heading_at_cpa": cpa_row["heading"],
            "cpa_lat": cpa_row["lat"],
            "cpa_lon": cpa_row["lon"],
            "relative_bearing_deg": round(bearing, 1),
            "quality_tag": quality_tag,
            "site_name": SITE_NAME
        })

    out_df = pd.DataFrame(transits)
    if out_df.empty:
        print(f"⚠️ No acoustically relevant transits found in {infile}")
        return

    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    out_df.to_csv(outfile, index=False)
    print(f"✅ Saved {len(out_df)} filtered transits → {outfile}")


# === Process selected date folders ===
def process_dates(date_folders):
    static_cache = load_static_cache()
    for d in date_folders:
        folder = os.path.join(BASE_DIR, d)
        if not os.path.isdir(folder):
            print(f"⚠️ Date folder missing: {folder}")
            continue

        out_folder = f"{folder}_transits_filtered"
        os.makedirs(out_folder, exist_ok=True)

        json_files = sorted(glob.glob(os.path.join(folder, "ais_raw_*.jsonl")))
        if not json_files:
            print(f"⚠️ No AIS files found in {folder}")
            continue

        print(f"\n📂 Processing folder: {folder}")
        for infile in json_files:
            outfile = os.path.join(
                out_folder,
                os.path.basename(infile).replace(".jsonl", "_transits_filtered.csv")
            )
            process_file(infile, outfile, static_cache)

    save_static_cache(static_cache)


def parse_args():
    parser = argparse.ArgumentParser(description="Filter AIS transits for Orcasound Lab site.")
    parser.add_argument("--date", help="UTC date (YYYYMMDD) to process; default is yesterday.")
    parser.add_argument("--all", action="store_true", help="Process all available date folders.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if not os.path.exists(BASE_DIR):
        print(f"❌ BASE_DIR does not exist: {BASE_DIR}")
        sys.exit(1)

    available = sorted([d for d in os.listdir(BASE_DIR) if d.isdigit()])
    if not available:
        print(f"⚠️ No date folders found in {BASE_DIR}")
        sys.exit(0)

    if args.all:
        targets = available
    else:
        target = args.date
        if not target:
            target = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")

        if target not in available:
            print(f"⚠️ Requested date {target} not found in {BASE_DIR}")
            sys.exit(0)
        targets = [target]

    print(f"🎯 Target dates: {', '.join(targets)}")
    process_dates(targets)
