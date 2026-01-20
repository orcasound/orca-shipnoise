# 📂 Shipnoise — Scripts Folder Documentation

This directory contains all automated processing logic for the Shipnoise AIS-to-audio pipeline.  
It is divided into **three logical stages**, with site-specific behavior fully parameterized and driven by external configuration.

Scripts/
├── collect/        # Live AIS data collection from AISstream
├── preprocess/     # Timeline utilities for aligning AIS and audio
└── process/        # Build transits, match AIS to audio, extract loudest segments

The Scripts/ directory is responsible for **data collection and processing only**.  
It does **not** handle frontend playback, orchestration, or long-term audio hosting.

---

## 1️⃣ collect/ — AIS Live Data Collection

These scripts connect to AISstream and record AIS messages for a **single hydrophone site per run**.

### Files
- ais_collect.py

### Purpose
ais_collect.py is a **single parameterized collector**, replacing all previous per-site collection scripts.

Example:
python ais_collect.py --site bush-point

The script:
- Opens a websocket connection to AISstream
- Fetches site configuration (latitude / longitude) from Orcasite’s GraphQL API
- Derives a geographic bounding box using a fixed collection radius
- Filters AIS messages within the site’s region
- Writes raw AIS messages to JSONL files
- Organizes output by UTC date folder (YYYYMMDD/)

Each run collects AIS data for a **fixed duration** (default: 3600 seconds) and then exits.

### Runtime model
- One site per process
- Process lifecycle (start, restart, scheduling) is managed externally (e.g. Fly.io)
- The script itself does **not** orchestrate multiple sites

These raw AIS logs are later consumed by processing jobs.

---

## 2️⃣ preprocess/ — Audio Timeline Preparation

### Files
- get_latest_timestamp.py

### Purpose
Hydrophone audio is served via **Orcasound public HLS streams** using timestamp-based segment filenames.

This script:
- Reads available audio segment filenames for each site
- Extracts start timestamps
- Produces a timeline CSV
- Enables precise alignment between AIS CPA timestamps and audio streams

This step must run before transit-to-audio matching.

---

## 3️⃣ process/ — AIS → Transit → Audio Processing Pipeline

This folder contains the **core processing logic** that converts AIS logs into structured vessel events and links them to audio.

All scripts are **parameterized by site** and intended to run as **scheduled jobs**.

---

### 3.1 — Transit Building  
ais_to_transits.py

#### Purpose
Convert raw AIS messages into structured **vessel transit events**.

The script:
- Loads AIS JSON logs for a given site and date
- Groups messages by MMSI
- Detects vessel entry and exit relative to the site region
- Computes CPA (Closest Point of Approach)
- Outputs a daily transit dataset

Example:
python ais_to_transits.py --site bush-point --date 20260102

This replaces all former ais_to_transits_<site>.py scripts.

---

### 3.2 — match_all_transits_to_ts.py

#### Purpose
Match each vessel’s **CPA timestamp** to the appropriate Orcasound audio stream.

The script:
- Loads transit outputs from step 3.1
- Reads audio timeline metadata from preprocess/
- Determines which HLS stream and segment cover the CPA moment
- Computes the relative offset within the stream

Resulting mapping:
CPA timestamp → HLS stream URI + offset

No audio is downloaded or re-encoded at this stage.

---

### 3.3 — merge_and_dedup.py

#### Purpose
Normalize and clean matched transit results.

The script:
- Merges intermediate outputs
- Removes duplicate transit events
- Normalizes timestamps and vessel identifiers
- Ensures only valid, unique events proceed downstream

---

### 3.4 — extract_loudest_segment.py

#### Purpose
Locate and register the **loudest 30-second audio window** around a vessel CPA using Orcasound HLS segments.

This script operates in **strict mode** and only records detections when a complete 30-second window can be constructed.

#### Logic Overview

For each _windowed_merged.csv file:
1. Parse candidate HLS segment ranges from segment_range
2. Download candidate .ts segments with retry logic
3. Convert segments to mono WAV and analyze loudness
4. Identify the loudest center segment
5. Classify ship-noise confidence
6. Require [previous, center, next] segments to be present
7. Insert detection metadata directly into the database

#### Key Characteristics
- Downloaded .ts and .wav files are temporary only
- No audio files are persisted
- Incomplete 30-second windows are dropped
- Results are written directly to the database
- Frontend playback uses stored HLS segment manifests

---

## 🧭 Pipeline Overview
```
AISstream
  ↓
collect/   (fixed-duration runs, one site per process)
  ↓
preprocess/
  ↓
process/   (scheduled jobs)
  ↓
Database (detections + HLS manifests)
  ↓
API / Shipnoise frontend (HLS seek & playback)
```
---

## ✅ Summary

The Scripts/ folder handles:
- Live AIS collection
- Vessel transit detection
- Alignment of AIS events with Orcasound audio
- Loudest-segment detection with strict 30-second validation

It does **not**:
- Host or re-upload audio
- Manage orchestration internally
- Perform ETL ingestion via intermediate files

All results reference **Orcasound’s existing HLS streams** as the authoritative audio source.
