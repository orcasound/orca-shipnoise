import sqlite3
import os

DB_PATH = os.getenv("DATABASE_PATH", "/app/data/shipnoise.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
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
    conn.commit()
    conn.close()
    print(f"[init_db] Database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_db()
