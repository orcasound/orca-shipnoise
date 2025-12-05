#!/bin/bash
# ===============================================================
# Script: upload_all_to_s3.sh
# Purpose: Upload all AIS project data (audio, metadata, raw AIS)
#          and safely delete local files older than 5 days.
# Schedule: Runs daily at UTC 09:00
# Logs: /home/ubuntu/aisstream/logs/upload_YYYYMMDD.log
# ===============================================================

set -euo pipefail

S3_BUCKET="shipnoise-data"
SITES=("Bush_Point" "Orcasound_Lab" "Port_Townsend" "Sunset_Bay")

# Use YESTERDAY UTC as the correct date for uploading
YESTERDAY=$(date -u -d "yesterday" +"%Y%m%d")
CUTOFF=$(date -u -d "5 days ago" +"%Y%m%d")
LOG_DIR="/home/ubuntu/aisstream/logs"
LOG_FILE="${LOG_DIR}/upload_${YESTERDAY}.log"

mkdir -p "$LOG_DIR"

{
  echo "==============================================================="
  echo "🕘 Upload started at $(date -u)"
  echo "Target bucket: $S3_BUCKET"
  echo "Uploading YESTERDAY (UTC): $YESTERDAY"
  echo "==============================================================="

  cd /home/ubuntu/aisstream/Sites || exit 1

  for site in "${SITES[@]}"; do
    site_dir="${site}_data"
    if [ ! -d "$site_dir" ]; then
      echo "⚠️  Directory $site_dir not found, skipping."
      continue
    fi

    echo ""
    echo "🚀 Processing $site_dir ..."
    cd "$site_dir"

    # === 1️⃣ Upload audio files ===
    if [ -d "output_audio" ]; then
      echo "   🎵 Uploading audio files..."
      aws s3 sync output_audio/ s3://$S3_BUCKET/audio/${site}/ \
        --exclude "*.tmp" --exclude "*.log"
    else
      echo "   ⚠️ No output_audio folder found."
    fi

    # === 2️⃣ Upload metadata CSVs ===
    echo "   🧾 Uploading metadata CSV files..."
    aws s3 sync . s3://$S3_BUCKET/metadata/${site}/ \
      --exclude "*" --include "*_output/*.csv"

    # === 3️⃣ Upload raw AIS JSON archives (YESTERDAY only) ===
    if [ -d "$YESTERDAY" ]; then
      tarfile="ais_raw_${YESTERDAY}.tar.gz"
      if [ ! -f "$tarfile" ]; then
        echo "   📦 Creating archive $tarfile..."
        tar -czf "$tarfile" "$YESTERDAY"/*.jsonl 2>/dev/null || echo "   ⚠️ No JSON files in $YESTERDAY/"
      fi
      echo "   ☁️ Uploading $tarfile to S3..."
      aws s3 cp "$tarfile" s3://$S3_BUCKET/raw_ais/${site}/${YESTERDAY}/
    else
      echo "   ⚠️ No folder for YESTERDAY ($YESTERDAY) found — nothing to upload."
    fi

    # === 4️⃣ Safe cleanup: remove folders older than 5 days ===
    echo "   🧹 Checking for old folders (before $CUTOFF)..."
    for dir in [0-9]*; do
      if [[ "$dir" =~ ^[0-9]{8}$ && "$dir" -lt "$CUTOFF" ]]; then
        echo "      🧽 Removing old folder: $dir"
        rm -rf -- "$dir"
      fi
    done

    find . -maxdepth 1 -type d -name '*_output' -mtime +5 -exec rm -rf -- {} \;
    find . -maxdepth 1 -type d -name '*_transits_filtered' -mtime +5 -exec rm -rf -- {} \;
    find . -maxdepth 1 -type f -name 'ais_raw_*.tar.gz' -mtime +5 -exec rm -f -- {} \;

    cd ..
  done

  echo ""
  echo "✅ All uploads and cleanup completed at $(date -u)"
  echo "==============================================================="

} | tee -a "$LOG_FILE"
