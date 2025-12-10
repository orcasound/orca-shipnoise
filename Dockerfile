# ===========================
# 1. Build Frontend (Next.js)
# ===========================
FROM node:20-bookworm AS frontend
WORKDIR /app

COPY frontend/package*.json ./
RUN npm install

COPY frontend ./
RUN npm run build


# ===========================
# 2. Backend build stage
# ===========================
FROM python:3.11-slim AS backend-build
WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./

RUN mkdir -p static
COPY --from=frontend /app/.next ./static/.next
COPY --from=frontend /app/public ./static/public


# ===========================
# 3. Final runtime image
# ===========================
FROM python:3.11-slim

WORKDIR /app

COPY --from=backend-build /app /app

COPY --from=backend-build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-build /usr/local/bin /usr/local/bin

EXPOSE 8080

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8080"]
