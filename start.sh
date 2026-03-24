#!/bin/bash
set -e

mkdir -p /app/data

# Restore database from S3 if backup exists
litestream restore -if-replica-exists -config /app/litestream.yml /app/data/shipnoise.db

# Initialize database schema (creates tables if they don't exist)
python /app/scripts/init_db.py

# Start API server
cd /app/backend && uvicorn api_server:app --host 0.0.0.0 --port 8080 &

# Start data pipeline
cd /app && python -u scripts/run_pipeline.py &

# Start Litestream replication
litestream replicate -config /app/litestream.yml &

# Wait for any process to exit
wait -n
kill $(jobs -p) 2>/dev/null
exit 1
