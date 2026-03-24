import os
import json
import sqlite3
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.environ.get("DATABASE_PATH", "/app/data/shipnoise.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def insert_detection(record):
    if isinstance(record.get("segment_details"), list):
        record["segment_details"] = json.dumps(record["segment_details"])

    sql = """
        INSERT INTO records (
            date, site, s3_bucket, mmsi, shipname, t_cpa,
            confidence, segment_details
        ) VALUES (
            :date, :site, :s3_bucket, :mmsi, :shipname, :t_cpa,
            :confidence, :segment_details
        )
    """
    try:
        with get_conn() as conn:
            conn.execute(sql, record)
            conn.commit()
    except Exception as e:
        print(f"[db] ERROR inserting detection for MMSI {record.get('mmsi')}: {e}")
