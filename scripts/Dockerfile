FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# System dependencies: ffmpeg for audio conversion, libsndfile for soundfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY scripts/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all scripts
COPY scripts/ ./scripts/

# Create Sites directory for intermediate data (ephemeral)
RUN mkdir -p /app/Sites

CMD ["python", "scripts/run_pipeline.py"]
