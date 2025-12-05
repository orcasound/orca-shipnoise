# 📂 Shipnoise — Scripts Folder Documentation

This directory contains all automated processing logic for the Shipnoise AIS-to-audio pipeline.  
It is divided into **three logical stages**:

```
Scripts/
├── collect/        # Live AIS data collection from AISstream
├── preprocess/     # Timeline utilities for aligning AIS and audio
├── process/        # Build transits, match audio, extract loudest clips
└── upload_all_to_s3.sh   # Daily S3 upload + cleanup automation
```

Each section below explains the purpose of every script inside these folders.

---

# 1️⃣ `collect/` — AIS Live Data Collection

These scripts connect to AISstream and continuously record AIS messages for each hydrophone site.

### Files
- `ais_collect_bush_point.py`
- `ais_collect_orcasound_lab.py`
- `ais_collect_port_townsend.py`
- `ais_collect_sunset_bay.py`
- `run_all_collect.sh`

### Purpose
- Open a websocket connection to AISstream  
- Filter messages around the site’s geographic bounding box  
- Save JSONL logs grouped by **UTC date folder (YYYYMMDD/)**  
- Run continuously under systemd timers  

These raw AIS logs are later processed into transits.

---

# 2️⃣ `preprocess/` — Audio Timeline Preparation

### Files
- `get_latest_timestamp.py`

### Purpose
Hydrophone audio files in S3 use timestamp-based filenames.  
This script:

- Reads the filenames for each site  
- Extracts the start timestamp of each audio file  
- Produces a timeline CSV (used by processing scripts)  
- Ensures AIS → audio matching can locate the correct file  

This is required before the processing stage can run.

---

# 3️⃣ `process/` — AIS → Transit → Audio Extraction Pipeline

This folder contains the **core logic** that converts AIS logs into audio clips.

---

## 3.1 — Transit Building Scripts  
`ais_to_transits_<site>.py`

Examples:
- `ais_to_transits_bush_point.py`
- `ais_to_transits_orcasound_lab.py`
- `ais_to_transits_port_townsend.py`
- `ais_to_transits_sunset_bay.py`

### Purpose
Convert raw AIS messages into structured **vessel transit events**.

Each script:
- Loads AIS JSON logs  
- Groups messages by MMSI  
- Detects when vessels enter / exit the site region  
- Computes **CPA (Closest Point of Approach)**  
- Outputs a daily transit list CSV  

This is the foundational step.

---

## 3.2 — `match_all_transits_to_ts.py`  
### Purpose
Match each vessel’s **CPA timestamp** to the correct **audio file** in S3.

The script:
- Loads transit CSVs from step 3.1  
- Reads audio timeline metadata (from `preprocess/`)  
- Determines which audio file covers the CPA moment  
- Produces a mapping such as:

```
CPA (timestamp) → audio file + relative window
```

This links AIS movement to the hydrophone audio.

---

## 3.3 — `merge_and_dedup.py`  
### Purpose
Normalize and clean the matched transit results.

The script:
- Merges intermediate CSV outputs  
- Removes duplicate transits  
- Cleans timestamp and ship name formats  
- Ensures only valid and unique events continue to the extraction stage  

This guarantees high-quality input for the next script.

---

## 3.4 — `extract_loudest_segment.py`  
### Purpose
Extract the **loudest 30-second audio clip** surrounding the CPA.

The script:
- Downloads or streams the audio file from S3  
- Analyzes dB levels near CPA  
- Locates the loudest 30-second window  
- Saves a WAV file locally  
- Computes metrics:
  - `mean_volume_db`
  - `max_volume_db`

It also outputs:

```
loudness_summary_YYYYMMDD.csv
```

This summary file is later imported into PostgreSQL by:

```
etl_from_loudness_summary.py
```

---

# 4️⃣ `upload_all_to_s3.sh` — Daily Automation

### Purpose
Upload all processed data to S3 and clean old files.

This script:

- Determines YESTERDAY (UTC)
- Uploads:
  - extracted audio clips  
  - metadata CSVs  
  - raw AIS archives  
- Deletes local data older than 5 days  
- Writes logs to `/home/ubuntu/aisstream/logs/`  

It is normally run via a daily systemd timer at:

```
UTC 09:00
```

---

# 🧭 Pipeline Overview Diagram

```
AISstream → collect/ → preprocess/ → process/ → S3 → backend ETL → PostgreSQL → API
```

This `Scripts/` directory contains everything up to the S3 upload step.

---

# ✅ Summary

The `Scripts/` folder automates the entire AIS → transit → audio extraction pipeline:

- Collect raw AIS  
- Build vessel transits  
- Match to hydrophone audio  
- Extract loudest CPA clips  
- Upload outputs to S3  

These results feed the backend API and the Shipnoise web interface.

