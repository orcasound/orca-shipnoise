# match_transits_to_clips.py
# Auto-detect latest *_transits.csv file if no explicit path is given

import pandas as pd
from dateutil import parser as dtparse
import glob, os

# Automatically find the newest *_transits.csv file
transit_files = sorted(glob.glob("*_transits.csv"))
if not transit_files:
    raise SystemExit("❌ No *_transits.csv file found in current directory.")
TRANSITS_CSV = transit_files[-1]   # pick the latest
print(f"[INFO] Using transits file: {TRANSITS_CSV}")

# Automatically find the newest *_clips_index.csv if exists, else fallback
clip_files = sorted(glob.glob("*_clips_index.csv"))
CLIPS_CSV = clip_files[-1] if clip_files else "audio_clips_index.csv"
print(f"[INFO] Using clips file: {CLIPS_CSV}")

def to_dt(s):
    return dtparse.parse(s) if not pd.isna(s) else None

def main():
    # --- Load transits ---
    t = pd.read_csv(TRANSITS_CSV)
    t["t_entry"] = t["t_entry"].apply(to_dt)
    t["t_cpa"]   = t["t_cpa"].apply(to_dt)
    t["t_exit"]  = t["t_exit"].apply(to_dt)

    # --- Load audio clips ---
    c = pd.read_csv(CLIPS_CSV)
    c["clip_start_utc"] = c["clip_start_utc"].apply(to_dt)
    c["clip_end_utc"]   = c["clip_end_utc"].apply(to_dt)

    rows = []
    for _, cr in c.iterrows():
        cs, ce = cr["clip_start_utc"], cr["clip_end_utc"]

        cand = t[(t["t_entry"] < ce) & (t["t_exit"] > cs)].copy()
        if cand.empty:
            rows.append({
                "clip_start_utc": cs.isoformat(),
                "clip_end_utc": ce.isoformat(),
                "overlap_count": 0,
                "top1_mmsi": None,
                "top1_shipname": None,
                "top1_cpa_dist_m": None,
            })
            continue

        # Compute overlap seconds
        cand["overlap_sec"] = [
            (min(ce, tr["t_exit"]) - max(cs, tr["t_entry"])).total_seconds()
            for _, tr in cand.iterrows()
        ]
        cand.sort_values("overlap_sec", ascending=False, inplace=True)
        top1 = cand.iloc[0]

        rows.append({
            "clip_start_utc": cs.isoformat(),
            "clip_end_utc": ce.isoformat(),
            "overlap_count": len(cand),
            "top1_mmsi": int(top1["mmsi"]),
            "top1_shipname": str(top1.get("shipname", "")).strip(),
            "top1_cpa_dist_m": float(top1.get("cpa_distance_m", -1)),
        })

    out_file = os.path.splitext(TRANSITS_CSV)[0] + "_annotated.csv"
    pd.DataFrame(rows).to_csv(out_file, index=False)
    print(f"✅ Saved -> {out_file}")

if __name__ == "__main__":
    main()

