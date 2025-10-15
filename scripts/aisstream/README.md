# ShipNoise Data Pipeline — AIS Collection & Hydrophone Matching

This folder contains Python scripts for collecting, processing, and matching AIS vessel data near hydrophone stations.  
The goal is to connect **vessel movement** (AIS) with **acoustic recordings** to analyze underwater noise impacts.

---

## ⚙️ Overview

| Stage | Script | Description |
|--------|---------|-------------|
| ① Data Collection | `ais_collect.py` | Collects raw AIS messages near a hydrophone (≈30 km radius). |
| ② Transit Extraction | `ais_to_transits.py` | Groups AIS messages into **ship transits** (entry → closest approach → exit) within 25 km. |
| ③ Audio Matching | `match_transits_to_clips.py` | Matches ship transits with **recorded audio clips** in time. |

---

## ① `ais_collect.py` — Real-time AIS Data Collection

Connects to the [AISstream.io](https://aisstream.io/) WebSocket API and saves all AIS messages for ships near the hydrophone.

### Configuration

| Parameter | Description |
|------------|--------------|
| `HYDRO_LAT`, `HYDRO_LON` | Latitude / longitude of the hydrophone |
| `R_KM` | Radius of collection area (km) |
| `DURATION_SECS` | Duration of each capture (e.g. 3600 = 1 h) |
| `AISSTREAM_API_KEY` | Stored securely as an environment variable (`export AISSTREAM_API_KEY="..."`) |

### Output
Files are saved under:
/home/ubuntu/aisstream/data/YYYYMMDD/ais_raw_YYYYMMDDTHHMMSSZ.jsonl

| Field                   | Meaning                   |
| ----------------------- | ------------------------- |
| `MMSI`                  | Vessel ID                 |
| `ShipName`              | Ship name                 |
| `Latitude`, `Longitude` | Vessel position           |
| `Sog`                   | Speed over ground (knots) |
| `Cog`                   | Course over ground (°)    |
| `TrueHeading`           | Vessel heading (°)        |
| `time_utc`              | UTC timestamp             |


## ② ais_to_transits.py — Identify Ship Transits

Processes raw .jsonl files to find when each vessel passes near the hydrophone (within 25 km).

Workflow

Reads ais_raw_*.jsonl files.

Computes Haversine distance for each message.

Groups by vessel mmsi.

Determines:

Entry (t_entry)

**Closest Point of Approach (CPA)** (t_cpa`)

Exit (t_exit)

Outputs one row per ship transit.

Output Example
*_transits.csv

mmsi	shipname	t_entry	t_cpa	t_exit	transit_duration_min	cpa_distance_m	sog_at_cpa	cog_at_cpa	heading_at_cpa
366945000	NAT GEO QUEST	2025-10-02T07:30Z	2025-10-02T07:47Z	2025-10-02T08:10Z	40.0	1843.5	7.9	306.7	303

| Column                         | Description                         |
| ------------------------------ | ----------------------------------- |
| `mmsi`                         | Vessel identifier                   |
| `shipname`                     | Name of vessel                      |
| `t_entry` / `t_exit`           | Entry and exit times for 25 km zone |
| `t_cpa`                        | Time of closest approach            |
| `cpa_distance_m`               | Distance (m) from hydrophone at CPA |
| `sog_at_cpa`                   | Speed (knots)                       |
| `cog_at_cpa`, `heading_at_cpa` | Vessel direction angles             |
| `transit_duration_min`         | Minutes inside 25 km radius         |

## ③ match_transits_to_clips.py — Match Ships to Audio Clips

This final script links the transit events to hydrophone audio clips based on time overlap.

Inputs

Transit file: the latest *_transits.csv (automatically detected) — contains ship movements and timestamps.

Clip index file: the latest *_clips_index.csv or audio_clips_index.csv — lists audio clip start and end times.

Each clip file contains:

| clip_id | clip_start_utc | clip_end_utc |
| ------- | -------------- | ------------ |

Logic

For each audio clip:

Find all transits overlapping the clip time window.

Compute overlap duration (overlap_sec).

Select the top-overlapping ship as top1_*.

Output
*_transits_annotated.csv

| clip_start_utc    | clip_end_utc      | overlap_count | top1_mmsi | top1_shipname | top1_cpa_dist_m |
| ----------------- | ----------------- | ------------- | --------- | ------------- | --------------- |
| 2025-10-02T07:45Z | 2025-10-02T08:00Z | 1             | 366945000 | NAT GEO QUEST | 1843.5          |

| Column                           | Description                              |
| -------------------------------- | ---------------------------------------- |
| `clip_start_utc`, `clip_end_utc` | Start / end of the audio clip            |
| `overlap_count`                  | Number of transits overlapping this clip |
| `top1_mmsi`, `top1_shipname`     | Most likely vessel producing sound       |
| `top1_cpa_dist_m`                | Ship–hydrophone distance at CPA          |

Script Outputs Summary

| Step  | Script                       | Description                                                                                     | Output Format                    | Example Filename                                  |
| ----- | ---------------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------- | ------------------------------------------------- |
| **①** | `ais_collect.py`             | Collects raw AIS messages (vessels within ~30 km of hydrophone) every 30 minutes                | **`.jsonl`** (one JSON per line) | `ais_raw_20251010T083000Z.jsonl`                  |
| **②** | `ais_to_transits.py`         | Processes raw AIS data to identify ship transits within 25 km radius (entry / exit / CPA times) | **`.csv`**                       | `ais_raw_20251010T083000Z_transits.csv`           |
| **③** | `match_transits_to_clips.py` | Matches each hydrophone audio clip with overlapping ship transits (temporal alignment)          | **`.csv`**                       | `ais_raw_20251010T083000Z_transits_annotated.csv` |

