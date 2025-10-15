# ais_to_transits_debug.py
# Debug version: generates transits and prints message stats.
# All output times are converted to UTC ISO8601 (with Z).

import json
import sys
import math
import os
import glob
import pandas as pd
from datetime import datetime, timezone

HYDRO_LAT, HYDRO_LON = 48.1358, -122.7596  # hydrophone coordinates
RADIUS_M = 25000  # analysis radius (m)

# --- Haversine distance in meters ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# --- Parse AIS timestamp string into datetime ---
def parse_time(ts_str):
    ts_str = ts_str.split(" +")[0]  # remove "+0000 UTC"
    try:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

# --- Convert datetime to UTC ISO8601 string ---
def to_utc_iso(dt):
    if pd.isna(dt):
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def process_file(infile, outfile):
    records = []
    cnt_position = 0
    cnt_static = 0
    cnt_other = 0
    cnt_decode_err = 0

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
            if mtype == "PositionReport":
                cnt_position += 1
                try:
                    m = msg["Message"]["PositionReport"]
                    meta = msg["MetaData"]
                    lat, lon = m["Latitude"], m["Longitude"]
                    t = parse_time(meta["time_utc"])
                    dist = haversine(HYDRO_LAT, HYDRO_LON, lat, lon)

                    records.append({
                        "mmsi": meta["MMSI"],
                        "shipname": meta.get("ShipName", "").strip(),
                        "time": t,
                        "lat": lat,
                        "lon": lon,
                        "sog": m["Sog"],
                        "cog": m["Cog"],
                        "heading": m["TrueHeading"],
                        "dist_m": dist
                    })
                except Exception:
                    continue
            elif mtype == "ShipStaticData":
                cnt_static += 1
            else:
                cnt_other += 1

    # Debug summary
    print(f"\n[DEBUG] File {infile}:")
    print(f"  PositionReport = {cnt_position}")
    print(f"  ShipStaticData = {cnt_static}")
    print(f"  Other messages = {cnt_other}")
    print(f"  JSON decode errors = {cnt_decode_err}")

    df = pd.DataFrame(records)
    if df.empty:
        print(f"⚠️ No valid transits found in {infile}")
        return

    transits = []
    for mmsi, group in df.groupby("mmsi"):
        g = group.sort_values("time")
        inside = g[g["dist_m"] < RADIUS_M]
        if inside.empty:
            continue

        t_entry = inside["time"].iloc[0]
        t_exit = inside["time"].iloc[-1]
        cpa_row = inside.loc[inside["dist_m"].idxmin()]

        transits.append({
            "mmsi": mmsi,
            "shipname": cpa_row["shipname"],
            "t_entry": to_utc_iso(t_entry),
            "t_cpa": to_utc_iso(cpa_row["time"]),
            "t_exit": to_utc_iso(t_exit),
            "transit_duration_min": round((t_exit - t_entry).total_seconds() / 60, 2),
            "cpa_distance_m": round(cpa_row["dist_m"], 1),
            "sog_at_cpa": cpa_row["sog"],
            "cog_at_cpa": cpa_row["cog"],
            "heading_at_cpa": cpa_row["heading"]
        })

    out_df = pd.DataFrame(transits)
    out_df.to_csv(outfile, index=False)
    print(f"✅ Saved {len(out_df)} transits to {outfile}")

def batch_process(folder):
    files = sorted(glob.glob(os.path.join(folder, "ais_raw_*.jsonl")))
    if not files:
        print("No input files found in", folder)
        return
    for infile in files:
        outfile = infile.replace(".jsonl", "_transits.csv")
        process_file(infile, outfile)

if __name__ == "__main__":
    if len(sys.argv) == 2 and os.path.isdir(sys.argv[1]):
        batch_process(sys.argv[1])
    elif len(sys.argv) == 3:
        process_file(sys.argv[1], sys.argv[2])
    else:
        print("Usage:")
        print("  python ais_to_transits_debug.py input.jsonl output.csv")
        print("  python ais_to_transits_debug.py /path/to/folder")
        sys.exit(1)

