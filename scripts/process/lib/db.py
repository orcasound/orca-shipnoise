import os
import json
import psycopg
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/home/ubuntu/aisstream/Scripts/process/.env")
DB_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg.connect(DB_URL)

def insert_detection(record):
    """
    Inserts a detection record into the database.
    Removed: lowfreq_ratio, spectral_entropy, ship_noise_index, segment_rms
    """
    
    if isinstance(record.get("segment_details"), list):
        record["segment_details"] = json.dumps(record["segment_details"])

    sql = """
        INSERT INTO records (
            date, site, s3_bucket, mmsi, shipname, t_cpa, 
            confidence, segment_details
        ) VALUES (
            %(date)s, %(site)s, %(s3_bucket)s, %(mmsi)s, %(shipname)s, %(t_cpa)s,
            %(confidence)s, %(segment_details)s
        )
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, record)
            conn.commit()
