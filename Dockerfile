# ===========================
# 1. Build Frontend (Next.js)
# ===========================
FROM node:20-bookworm AS frontend

WORKDIR /app

# Install dependencies (cached)
COPY frontend/package*.json ./
RUN npm install

# Copy source
COPY frontend ./

# Build production bundle
RUN npm run build


# ===========================
# 2. Build Backend (FastAPI)
# ===========================
FROM python:3.11-slim AS backend

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend ./

# Prepare static folder
RUN mkdir -p static

# Copy built frontend into backend static folder
COPY --from=frontend /app/.next ./static/.next
COPY --from=frontend /app/public ./static/public


# ===========================
# 3. Final Runtime Image
# ===========================
FROM python:3.11-slim

WORKDIR /app

# Copy built backend + frontend assets
COPY --from=backend /app /app

# Expose port 8080 for FastAPI + Fly.io
EXPOSE 8080

# Start FastAPI server
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8080"]
