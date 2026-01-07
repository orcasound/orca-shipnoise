#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stage-3D: extract_loudest_segment.py
------------------------------------
Logic:
  1. Reads *_windowed_merged.csv (valid ranges).
  2. Downloads segments to find the Loudest (Center).
  3. STRICT MODE: actively secures Previous and Next segments (Retry logic).
  4. Inserts only if 3 segments (30s) are successfully secured.
"""

import os
import argparse
import tempfile
import requests
import subprocess
import numpy as np
import pandas as pd
import time
import shutil
from scipy.io import wavfile

# Import DB function
from lib.db import insert_detection

# ---------------- Utility ----------------

def vprint(verbose: bool, msg: str):
    if verbose:
        print(msg)

# ---------------- Audio Analysis ----------------

def rms_db(wav_path: str):
    try:
        rate, data = wavfile.read(wav_path)
        if getattr(data, "ndim", 1) > 1:
            data = data.mean(axis=1)
        data = data.astype(float)
        if len(data) == 0:
            return np.nan, np.nan, np.nan
        rms = float(np.sqrt(np.mean(np.square(data))))
        mean_db = 20.0 * np.log10(rms + 1e-9)
        max_db = 20.0 * np.log10(np.max(np.abs(data)) + 1e-9)
        return rms, mean_db, max_db
    except Exception as e:
        # vprint(True, f"⚠️ RMS Error {os.path.basename(wav_path)}: {e}")
        return np.nan, np.nan, np.nan

def compute_lowfreq_ratio(wav_path: str):
    try:
        rate, data = wavfile.read(wav_path)
        if getattr(data, "ndim", 1) > 1:
            data = data.mean(axis=1)
        data = data.astype(float)
        if len(data) == 0:
            return np.nan, np.nan, np.nan, np.nan

        fft = np.fft.rfft(data)
        freqs = np.fft.rfftfreq(len(data), d=1.0 / rate)
        power = np.abs(fft) ** 2
        total = float(np.sum(power))
        if total <= 0:
            return np.nan, np.nan, np.nan, np.nan

        low = float(np.sum(power[(freqs >= 10) & (freqs < 200)]))
        mid = float(np.sum(power[(freqs >= 200) & (freqs < 2000)]))
        ratio = low / (mid + 1e-9)
        delta_L = 10.0 * np.log10((low + 1e-9) / (mid + 1e-9))

        p = power / (total + 1e-12)
        entropy = float(-np.sum(p * np.log2(p + 1e-12)))

        H_bg = 16.0
        ship_index = 0.7 * ratio + 0.3 * (H_bg - entropy)
        return ratio, entropy, delta_L, ship_index
    except Exception:
        return np.nan, np.nan, np.nan, np.nan

def classify_confidence(ratio, entropy=None, delta_L=None, site_name=None):
    if site_name == "Sunset_Bay":
        if np.isnan(ratio): return "none"
        if ratio > 2 or (delta_L is not None and delta_L > 4): return "high"
        elif ratio > 0.2 or (delta_L is not None and delta_L > -2): return "medium"
        elif ratio > 0.05 or (delta_L is not None and delta_L > -8): return "low"
        else: return "none"
    
    if np.isnan(ratio): return "none"
    if ratio > 5 or (delta_L is not None and delta_L > 6): return "high"
    elif ratio > 0.5 or (delta_L is not None and delta_L > -1): return "medium"
    elif ratio >= 0.1 or (delta_L is not None and delta_L > -6): return "none"
    else: return "none"

# ---------------- Network Logic (Retry) ----------------

def download_ts_retry(s3_prefix: str, folder: str, seg_int: int, tmp_dir: str, verbose: bool, retries=3):
    """
    Downloads segment with RETRY logic. Returns local path or None.
    """
    base_url = f"https://audio-orcasound-net.s3.amazonaws.com/{s3_prefix}/hls/{folder}"
    local = os.path.join(tmp_dir, f"{folder}_live{seg_int}.ts")
    
    # Try plain and padded (live1.ts vs live001.ts)
    urls_to_try = [f"{base_url}/live{seg_int}.ts", f"{base_url}/live{seg_int:03d}.ts"]

    for url in urls_to_try:
        for attempt in range(retries):
            try:
                # vprint(verbose, f"      ⬇️ Downloading {url}...")
                r = requests.get(url, timeout=10)
                
                if r.status_code == 404:
                    # 404 means file not found. Wait briefly and retry in case of eventual consistency?
                    # Usually 404 is hard fail, but let's sleep 1s just in case logic is faster than upload.
                    time.sleep(1)
                    if attempt == retries - 1: break # Give up on this URL format
                    continue

                r.raise_for_status()
                if len(r.content) == 0:
                    raise ValueError("Empty Content")

                with open(local, "wb") as f:
                    f.write(r.content)
                return local # Success

            except Exception as e:
                # Network or Timeout
                if attempt < retries - 1:
                    time.sleep(1) # Wait before retry
                else:
                    if verbose: print(f"      ❌ Failed {url}: {e}")
    return None

def parse_segment_ranges(seg_raw: str):
    parts = [p.strip() for p in seg_raw.split(",") if p.strip()]
    ranges = []
    for p in parts:
        p = p.replace("–", "-").replace("—", "-")
        if "/" not in p or "live" not in p or "-" not in p: continue
        try:
            folder = p.split("/")[0].strip()
            left, right = p.split("/")[-1].split("-")
            left = int(left.split("live")[-1])
            right = int(right.split("live")[-1])
            if right < left: left, right = right, left
            ranges.append({"folder": folder, "start": left, "end": right})
        except:
            continue
    return ranges

# ---------------- Processing ----------------

def process_csv(site, site_dir, s3_prefix, csv_path, verbose):
    site_name = site.replace("_", " ").title().replace(" ", "_")
    print(f"📄 Processing {os.path.basename(csv_path)}")
    
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]

    for idx, row in df.iterrows():
        seg_raw = str(row.get("segment_range", "")).strip()
        ranges = parse_segment_ranges(seg_raw)
        if not ranges: continue

        with tempfile.TemporaryDirectory() as tmp_dir:
            wav_files = [] 
            
            # 1. Download Search Range
            for r in ranges:
                folder, a, b = r["folder"], r["start"], r["end"]
                for seg_int in range(a, b + 1):
                    ts_path = download_ts_retry(s3_prefix, folder, seg_int, tmp_dir, verbose)
                    if not ts_path: continue
                    
                    wav_path = ts_path.replace(".ts", ".wav")
                    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", ts_path, "-ac", "1", "-ar", "48000", wav_path], check=False)
                    wav_files.append((folder, seg_int, wav_path))

            if not wav_files: continue

            # 2. Find Loudest
            loud_folder, loud_seg_int, loud_wav = max(wav_files, key=lambda t: rms_db(t[2])[0])

            # 3. Confidence Check
            rms, mean_db, max_db = rms_db(loud_wav)
            ratio, entropy, delta_L, ship_index = compute_lowfreq_ratio(loud_wav)
            conf = classify_confidence(ratio, entropy, delta_L, site_name)

            # Warning: Bush Point silent files (Jan 4) might fail this check and be skipped!
            # If you want to force test, comment out the next two lines.
            if conf == "none":
                 # vprint(verbose, f"   Skipping {row.get('shipname')}: Low confidence/Silence.")
                 continue

            # 4. Strict 30s Manifest Construction
            # We want [Prev, Center, Next]
            final_manifest = []
            
            # Define the 3 targets: (folder, seg_int)
            # Simplification: Assume same folder for neighbors unless logic requires jump (omitted for brevity, usually same folder)
            targets = [
                (loud_folder, loud_seg_int - 1), # Prev
                (loud_folder, loud_seg_int),     # Center
                (loud_folder, loud_seg_int + 1)  # Next
            ]

            all_secured = True
            for fldr, seg in targets:
                local_ts = os.path.join(tmp_dir, f"{fldr}_live{seg}.ts")
                
                # If not downloaded yet (e.g. neighbor was outside search range), fetch now
                if not os.path.exists(local_ts):
                    vprint(verbose, f"      ⬇️ Fetching missing neighbor {fldr}/live{seg}...")
                    dl_path = download_ts_retry(s3_prefix, fldr, seg, tmp_dir, verbose)
                    if not dl_path:
                        vprint(verbose, f"      ❌ Missing segment {fldr}/live{seg}. Skipping record (Strict 30s).")
                        all_secured = False
                        break
                
                final_manifest.append(f"{fldr}/live{seg:03d}.ts")

            if not all_secured:
                continue

            # 5. Insert
            insert_detection({
                "date": os.path.basename(csv_path).split("_")[0],
                "site": site,
                "s3_bucket": s3_prefix,
                "mmsi": row.get("mmsi"),
                "shipname": row.get("shipname"),
                "t_cpa": row.get("t_cpa"),
                "confidence": conf,
                "segment_details": final_manifest 
            })
            vprint(verbose, f"🔊 [{site}] {row.get('shipname')} - Inserted 30s clip.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", required=True)
    parser.add_argument("--date", nargs="*")
    parser.add_argument("--target_date", help="Ignored, compatibility only")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    base_dir = "/home/ubuntu/aisstream/Sites"
    sites = {
        "bush_point": "rpi_bush_point",
        "orcasound_lab": "rpi_orcasound_lab",
        "port_townsend": "rpi_port_townsend",
        "sunset_bay": "rpi_sunset_bay",
    }

    target_sites = sites.keys() if args.site == "all" else [args.site]
    
    for site in target_sites:
        formatted_name = site.replace("_", " ").title().replace(" ", "_")
        site_dir = os.path.join(base_dir, f"{formatted_name}_data")
        if not os.path.isdir(site_dir): continue

        dates = args.date if args.date else []
        # If no date provided, logic to scan all folders (omitted here for specific run)
        
        for ymd in dates:
            csv_dir = os.path.join(site_dir, f"{ymd}_output")
            if not os.path.exists(csv_dir): 
                print(f"Directory not found: {csv_dir}")
                continue
            
            for fname in sorted(os.listdir(csv_dir)):
                if fname.endswith("_windowed_merged.csv"):
                    process_csv(site, site_dir, sites[site], os.path.join(csv_dir, fname), args.verbose)

if __name__ == "__main__":
    main()
