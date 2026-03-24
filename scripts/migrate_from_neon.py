"""
One-time migration script: Neon (PostgreSQL) → SQLite

Usage (inside fly machine):
  python /app/scripts/migrate_from_neon.py

Requires NEON_DATABASE_URL environment variable to be set.
"""
import os
import sqlite3
import json

DB_PATH = os.getenv("DATABASE_PATH", "/app/data/shipnoise.db")
NEON_URL = os.getenv("NEON_DATABASE_URL")

if not NEON_URL:
    raise SystemExit("Please set NEON_DATABASE_URL environment variable.")

try:
    import psycopg2
except ImportError:
    raise SystemExit("psycopg2 not installed. Run: pip install psycopg2-binary")

print(f"[migrate] Connecting to Neon...")
pg_conn = psycopg2.connect(NEON_URL)
pg_cur = pg_conn.cursor()

pg_cur.execute("SELECT id, date, site, s3_bucket, mmsi, shipname, t_cpa, confidence, segment_details FROM records")
rows = pg_cur.fetchall()
print(f"[migrate] Found {len(rows)} records in Neon")

print(f"[migrate] Writing to SQLite at {DB_PATH}...")
sqlite_conn = sqlite3.connect(DB_PATH)
sqlite_conn.execute("""
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        site TEXT,
        s3_bucket TEXT,
        mmsi INTEGER,
        shipname TEXT,
        t_cpa REAL,
        confidence REAL,
        segment_details TEXT
    )
""")

for row in rows:
    id_, date, site, s3_bucket, mmsi, shipname, t_cpa, confidence, segment_details = row
    if isinstance(segment_details, list):
        segment_details = json.dumps(segment_details)
    sqlite_conn.execute("""
        INSERT OR IGNORE INTO records (id, date, site, s3_bucket, mmsi, shipname, t_cpa, confidence, segment_details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (id_, date, site, s3_bucket, mmsi, shipname, t_cpa, confidence, segment_details))

sqlite_conn.commit()
sqlite_conn.close()
pg_conn.close()

print(f"[migrate] Done! {len(rows)} records migrated.")
