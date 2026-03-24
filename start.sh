#!/bin/bash
set -e

# Start the API server
cd /app/backend && uvicorn api_server:app --host 0.0.0.0 --port 8080 &

# Start the data pipeline
cd /app && python -u scripts/run_pipeline.py &

# Wait for either process to exit
wait -n

# If one exits, kill the other and exit
kill $(jobs -p) 2>/dev/null
exit 1
