import os
import json
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "/app/data/shipnoise.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def insert_detection(record):
    """
    Inserts a detection record into the database.
    """
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
        conn = get_conn()
        conn.execute(sql, record)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[db] ERROR inserting detection for MMSI {record.get('mmsi')}: {e}")
