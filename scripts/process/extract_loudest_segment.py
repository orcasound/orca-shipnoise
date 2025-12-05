#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage-3D: extract_loudest_segment.py
------------------------------------
Adds cross-day (cross-session) 2-segment merge while keeping your existing logic:
- Reads *_windowed_merged.csv (which may contain multiple session ranges, e.g.
  "1763366711/live8591-live8608, 1763452821/live0-live16").
- Downloads segments; tries both unpadded (liveN.ts) and zero-padded (liveNNN.ts).
- Picks the loudest single segment by RMS.
- Then tries to merge TWO consecutive segments:
    1) Prefer (N, N+1) inside the SAME session.
    2) If at the end of a session, try the START of the NEXT session (cross-day).
    3) If (N+1) fails, try (N-1, N); if at the start of a session, try the END of the PREV session.
  If no neighbor is available, keeps the single-segment clip.
- Keeps 3-digit zero-pad for segment labels in names/CSV (e.g. live086).
- Log lines include the site name:  🔊 [Bush_Point] MMSI SHIP — ...
- Output CSV columns unchanged (extended set you requested).

CSV columns produced:
  date,mmsi,shipname,site_name,aws_prefix,aws_folder,segment_range,
  loudest_seg,merged_segs,seg_start,seg_end,t_cpa,cpa_distance_m,
  mean_volume_db,max_volume_db,lowfreq_ratio,spectral_entropy,
  ship_noise_index,acoustic_confidence,clip_duration_sec,
  output_audio,segment_rms
"""

import os
import sys
import argparse
import tempfile
import shutil
import requests
import subprocess
import numpy as np
import pandas as pd
from scipy.io import wavfile

# --------- Utility printing ---------
def vprint(verbose: bool, msg: str):
    if verbose:
        print(msg)

# --------- Audio math ---------
def rms_db(wav_path: str):
    """Return (RMS_linear, mean_dB, max_dB) for a mono or stereo WAV."""
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
        print(f"⚠️  Failed RMS computation for {os.path.basename(wav_path)}: {e}")
        return np.nan, np.nan, np.nan

def compute_lowfreq_ratio(wav_path: str):
    """Return (ratio, entropy, delta_L, ship_index)."""
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
    except Exception as e:
        print(f"⚠️  Failed spectral analysis for {os.path.basename(wav_path)}: {e}")
        return np.nan, np.nan, np.nan, np.nan

def classify_confidence(ratio, entropy=None, delta_L=None,site_name=None):
    

    # ----- Sunset Bay uses custom thresholds -----
    if site_name == "Sunset_Bay":
        if np.isnan(ratio):
            return "none"
        if ratio > 2 or (delta_L is not None and delta_L > 4):
            return "high"
        elif ratio > 0.2 or (delta_L is not None and delta_L > -2):
            return "medium"
        elif ratio > 0.05 or (delta_L is not None and delta_L > -8):
            return "low"
        else:
            return "none" 
    if np.isnan(ratio):
        return "none"
    if ratio > 5 or (delta_L is not None and delta_L > 6):
        return "high"
    elif ratio > 0.5 or (delta_L is not None and delta_L > -1):
        return "medium"
    elif ratio >= 0.1 or (delta_L is not None and delta_L > -6):
        return "none"
    else:
        return "none"

# --------- Network download ---------
def download_ts(s3_prefix: str, folder: str, seg_int: int, tmp_dir: str, verbose: bool):
    """
    Try both unpadded and zero-padded URLs for segment download.
    Saves to <tmp_dir>/<folder>_live<seg_int>.ts and returns that path, or None.
    """
    base_url = f"https://audio-orcasound-net.s3.amazonaws.com/{s3_prefix}/hls/{folder}"
    local = os.path.join(tmp_dir, f"{folder}_live{seg_int}.ts")
    url_plain  = f"{base_url}/live{seg_int}.ts"
    url_padded = f"{base_url}/live{seg_int:03d}.ts"

    for url in (url_plain, url_padded):
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 404:
                vprint(verbose, f"🚫 Missing segment: {url}")
                continue
            r.raise_for_status()
            with open(local, "wb") as f:
                f.write(r.content)
            if url is url_padded:
                vprint(verbose, f"✅ Found padded file: {url}")
            return local
        except Exception as e:
            vprint(verbose, f"⚠️  Failed to download {url} — {e}")
            continue
    vprint(verbose, f"⛔️ TS segment {seg_int} download failed ({folder})")
    return None

# --------- CSV helpers ---------
def parse_segment_ranges(seg_raw: str):
    """
    Parse "1763366711/live8591-live8608, 1763452821/live0-live16"
    -> [{'folder': '1763366711', 'start': 8591, 'end': 8608},
        {'folder': '1763452821', 'start':    0, 'end':   16}]
    Order is preserved to know previous/next sessions for cross-day stitching.
    """
    parts = [p.strip() for p in seg_raw.split(",") if p.strip()]
    ranges = []
    for p in parts:
        p = p.replace("–", "-").replace("—", "-")  # normalize Unicode dashes
        if "/" not in p or "live" not in p or "-" not in p:
            continue
        folder = p.split("/")[0].strip()
        left, right = p.split("/")[-1].split("-")
        if "live" in left:
            left = left.split("live")[-1]
        if "live" in right:
            right = right.split("live")[-1]
        try:
            a = int(left); b = int(right)
            if b < a:
                a, b = b, a
            ranges.append({"folder": folder, "start": a, "end": b})
        except ValueError:
            continue
    return ranges

def ffmpeg_concat_wavs(wav_paths, out_path):
    """
    Concatenate 2 WAV files into one WAV using ffmpeg concat demuxer.
    If only 1 path provided, just copy it.
    """
    if len(wav_paths) == 1:
        shutil.copy2(wav_paths[0], out_path)
        return True
    list_file = out_path + ".list.txt"
    with open(list_file, "w") as f:
        for p in wav_paths:
            f.write(f"file '{p}'\n")
    cmd = ["ffmpeg", "-loglevel", "error", "-y",
           "-f", "concat", "-safe", "0",
           "-i", list_file, "-c", "copy", out_path]
    try:
        subprocess.run(cmd, check=True)
        os.remove(list_file)
        return True
    except Exception:
        try: os.remove(list_file)
        except Exception: pass
        return False

# --------- Core processing ---------
def process_day(site_dir: str, s3_prefix: str, csv_path: str, verbose: bool = False):
    """
    Process one *_windowed_merged.csv:
      - Download all segments in the listed ranges.
      - Pick the loudest single segment by RMS.
      - Try to add an adjacent segment; if at a session boundary, cross into the
        next/prev session's boundary segment for a 2-seg merge.
      - Save final WAV and extended CSV.
    """
    date = os.path.basename(csv_path).split("_")[0]
    audio_dir = os.path.join(site_dir, "output_audio", date)
    os.makedirs(audio_dir, exist_ok=True)

    site_name = os.path.basename(site_dir).replace("_data", "")
    aws_prefix = s3_prefix

    print(f"📄 Reading CSV: {csv_path}")
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    summary = []

    for idx, row in df.iterrows():
        seg_raw = str(row.get("segment_range", "")).strip()
        vprint(verbose, f"[DEBUG] Row {idx} segment_range = {repr(seg_raw)}")
        if not seg_raw:
            vprint(verbose, "[DEBUG] ⛔️ Skipped: empty segment_range")
            continue

        ranges = parse_segment_ranges(seg_raw)
        if not ranges:
            vprint(verbose, "[DEBUG] ⛔️ Skipped: cannot parse ranges")
            continue

        tmp_dir = tempfile.mkdtemp(dir=audio_dir)
        wav_files = []  # list of (folder, seg_int, wav_path)
        for r in ranges:
            folder, a, b = r["folder"], r["start"], r["end"]
            vprint(verbose, f"[DEBUG]   ↳ folder={folder} range=live{a}-live{b}")
            for seg_int in range(a, b + 1):
                ts_path = download_ts(aws_prefix, folder, seg_int, tmp_dir, verbose)
                if not ts_path:
                    continue
                wav_path = ts_path.replace(".ts", ".wav")
                subprocess.run(
                    ["ffmpeg", "-loglevel", "error", "-y",
                     "-i", ts_path, "-ac", "1", "-ar", "48000", "-acodec", "pcm_s16le", wav_path],
                    check=False
                )
                wav_files.append((folder, seg_int, wav_path))

        if not wav_files:
            vprint(verbose, f"[DEBUG] ⛔️ No WAV files generated for row {idx}, skipping")
            shutil.rmtree(tmp_dir, ignore_errors=True)
            continue

        vprint(verbose, f"[DEBUG] {len(wav_files)} wav files generated")

        # Pick loudest single segment
        loud_folder, loud_seg_int, loud_wav = max(wav_files, key=lambda t: rms_db(t[2])[0])

        # Build fast lookup and range index for cross-session neighbor logic
        candidates = {(f, s): p for (f, s, p) in wav_files}
        folder_to_range_idx = {r["folder"]: i for i, r in enumerate(ranges)}

        def neighbor_after(folder: str, seg: int):
            """Try (folder, seg+1); if at end of that folder's range, jump to next folder's start."""
            # Same-folder neighbor
            if (folder, seg + 1) in candidates:
                return folder, seg + 1
            # Cross to next session if we are at the end of this session
            ridx = folder_to_range_idx.get(folder, None)
            if ridx is not None:
                r = ranges[ridx]
                if seg >= r["end"] and ridx + 1 < len(ranges):
                    next_r = ranges[ridx + 1]
                    # Prefer exact start of next session (often 0)
                    for start_candidate in (next_r["start"],):
                        if (next_r["folder"], start_candidate) in candidates:
                            return next_r["folder"], start_candidate
            return None

        def neighbor_before(folder: str, seg: int):
            """Try (folder, seg-1); if at start of the folder's range, jump to prev folder's end."""
            # Same-folder neighbor
            if (folder, seg - 1) in candidates:
                return folder, seg - 1
            # Cross to prev session if we are at the start of this session
            ridx = folder_to_range_idx.get(folder, None)
            if ridx is not None:
                r = ranges[ridx]
                if seg <= r["start"] and ridx - 1 >= 0:
                    prev_r = ranges[ridx - 1]
                    for end_candidate in (prev_r["end"],):
                        if (prev_r["folder"], end_candidate) in candidates:
                            return prev_r["folder"], end_candidate
            return None

        # Choose up to TWO segments for final clip
        wavs_to_merge = [loud_wav]
        pair = (loud_folder, loud_seg_int)

        nb = neighbor_after(loud_folder, loud_seg_int)
        if nb:
            wavs_to_merge.append(candidates[nb])
            pair = (pair, nb)
        else:
            nb = neighbor_before(loud_folder, loud_seg_int)
            if nb:
                wavs_to_merge.insert(0, candidates[nb])
                pair = (nb, pair)

        # Output filename based on loudest segment (3-digit)
        mmsi = row.get("mmsi", "")
        shipname = str(row.get("shipname", "")).strip()
        loud_seg_str = f"{loud_seg_int:03d}"
        out_name = f"{mmsi}_{shipname.replace(' ', '_')}_live{loud_seg_str}_30s.wav"
        out_path = os.path.join(audio_dir, out_name)

        ok = ffmpeg_concat_wavs(wavs_to_merge, out_path)
        if not ok:
            vprint(verbose, f"[DEBUG] ⛔️ Concat failed; fall back to single loudest file")
            shutil.copy2(loud_wav, out_path)

        # Re-measure on the final saved clip
        rms, mean_dB, max_dB = rms_db(out_path)
        ratio, entropy, delta_L, ship_index = compute_lowfreq_ratio(out_path)
        conf = classify_confidence(ratio, entropy, delta_L,site_name)

        # Site-tagged log line (unchanged metrics formatting)
        vprint(verbose, f"🔊 [{site_name}] {mmsi} {shipname:25s} — mean_dB={mean_dB:.1f}, max_dB={max_dB:.1f}, RMS={rms:.5f}, ratio={ratio:.3f}, conf={conf}")

        if conf =="none":
            vprint(verbose, f"❎ Filtered out (confidence={conf}) → {os.path.basename(out_path)}")
            try: os.remove(out_path)
            except Exception: pass
            shutil.rmtree(tmp_dir, ignore_errors=True)
            continue

        seg_start_int = min(s for _, s, _ in wav_files)
        seg_end_int   = max(s for _, s, _ in wav_files)
        seg_start_str = f"{seg_start_int:03d}"
        seg_end_str   = f"{seg_end_int:03d}"
        merged_segs_count = 2 if len(wavs_to_merge) == 2 else 1

        shutil.rmtree(tmp_dir, ignore_errors=True)

        summary.append({
            "date": date,
            "mmsi": mmsi,
            "shipname": shipname,
            "site_name": site_name,
            "aws_prefix": aws_prefix,
            "aws_folder": loud_folder,
            "segment_range": seg_raw,
            "loudest_seg": loud_seg_str,
            "merged_segs": merged_segs_count,
            "seg_start": seg_start_str,
            "seg_end": seg_end_str,
            "t_cpa": row.get("t_cpa",""),
            "cpa_distance_m": row.get("cpa_distance_m",""),
            "mean_volume_db": mean_dB,
            "max_volume_db": max_dB,
            "lowfreq_ratio": ratio,
            "spectral_entropy": entropy,
            "ship_noise_index": ship_index,
            "acoustic_confidence": conf,
            "clip_duration_sec": "",
            "output_audio": out_path,
            "segment_rms": rms
        })

    if summary:
        out_csv = os.path.join(audio_dir, f"loudness_summary_{date}.csv")
        pd.DataFrame(summary).to_csv(out_csv, index=False)
        print(f"🧾 Saved summary → {out_csv}")
    else:
        print("ℹ️  No qualifying rows; nothing saved.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", required=True,
                        help="bush_point|orcasound_lab|port_townsend|sunset_bay|all")
    parser.add_argument("--date", nargs="*",
                        help="YYYYMMDD; omit to auto-scan all <YYYYMMDD>_output")
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
        site_dir = os.path.join(base_dir, f"{'_'.join([w.capitalize() for w in site.split('_')])}_data")
        if not os.path.isdir(site_dir):
            print(f"[SKIP] Missing site dir: {site_dir}")
            continue

        # Auto-scan dates if not provided: find all <YYYYMMDD>_output dirs
        if args.date:
            date_list = args.date
        else:
            date_list = []
            for d in sorted(os.listdir(site_dir)):
                if d.endswith("_output") and os.path.isdir(os.path.join(site_dir, d)):
                    date_list.append(d.replace("_output", ""))

        for ymd in date_list:
            csv_dir = os.path.join(site_dir, f"{ymd}_output")
            # Prefer *_windowed_merged.csv; if multiple, process all
            for fname in sorted(os.listdir(csv_dir)):
                if fname.endswith("_windowed_merged.csv"):
                    csv_path = os.path.join(csv_dir, fname)
                    process_day(site_dir, sites[site], csv_path, verbose=args.verbose)

if __name__ == "__main__":
    main()
