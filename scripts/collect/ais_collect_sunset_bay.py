# ais_collect_sunset_bay.py
import os, json, math, asyncio, websockets
from datetime import datetime, timezone, timedelta
from pathlib import Path

# === REQUIRED: Your AISstream API Key (or set env var: export AISSTREAM_API_KEY="xxx") ===
API_KEY = os.getenv("AISSTREAM_API_KEY")
if not API_KEY:
    raise SystemExit("Please set AISSTREAM_API_KEY environment variable.")

# === REQUIRED: Hydrophone configuration ===
SITE_NAME = "Sunset_Bay"
HYDRO_LAT, HYDRO_LON = 47.86497296593844, -122.33393605795372

# === Size of subscription bounding box (km) around the hydrophone (recommend: 30 km) ===
R_KM = 30.0

# === Duration of data collection in seconds (default 3600 s = 1 h) ===
def resolve_duration(default: int = 3600) -> int:
    """Read AIS_DURATION_SECS env var if set, otherwise use default."""
    raw = os.getenv("AIS_DURATION_SECS", "")
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        print(f"Invalid AIS_DURATION_SECS={raw!r}; falling back to {default}")
        return default

DURATION_SECS = resolve_duration()

# --- Base path (auto-detect project root containing Sites/) ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = PROJECT_ROOT / "Sites" / f"{SITE_NAME}_data"
BASE_DIR.mkdir(parents=True, exist_ok=True)

# --- Convert radius in km to a bounding box (lat/lon rectangle) ---
def bbox_from_radius_km(lat, lon, r_km):
    # 1 degree latitude ≈ 111 km; longitude scales with cos(lat)
    dlat = r_km / 111.0
    dlon = r_km / (111.0 * max(0.1, math.cos(math.radians(lat))))
    # [[lat_min, lon_min], [lat_max, lon_max]]
    return [[lat - dlat, lon - dlon], [lat + dlat, lon + dlon]]

async def collect_once(out_path: str):
    uri = "wss://stream.aisstream.io/v0/stream"
    bbox = bbox_from_radius_km(HYDRO_LAT, HYDRO_LON, R_KM)

    sub_msg = {
        "APIKey": API_KEY,
        "BoundingBoxes": [bbox],  # list of bounding boxes
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"]
    }

    print(f"Connecting... {uri}  BBOX={bbox}")
    start = datetime.now(timezone.utc)
    deadline = start + timedelta(seconds=DURATION_SECS)

    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps(sub_msg))
        print("Subscription sent. Waiting for data...")

        cnt = 0
        with open(out_path, "w", encoding="utf-8") as f:
            async for msg in ws:
                now = datetime.now(timezone.utc)
                if now >= deadline:
                    break
                # Websockets returns bytes → decode to string
                if isinstance(msg, (bytes, bytearray)):
                    msg = msg.decode("utf-8", errors="ignore")
                f.write(msg.strip() + "\n")
                cnt += 1
                if cnt % 200 == 0:
                    print(f"[{now.isoformat()}] received {cnt} messages...")
        print(f"Saved: {out_path}  (messages={cnt})")

async def main():
    # Output file is named with UTC timestamp
    # === Create dated folder automatically ===
    now = datetime.now(timezone.utc)
    date_folder = now.strftime("%Y%m%d")
    out_dir = BASE_DIR / date_folder
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"ais_raw_{now.strftime('%Y%m%dT%H%M%SZ')}.jsonl"


    # Simple auto-reconnect: if error, wait 5s and retry until deadline
    try:
        await collect_once(out_file)
    except Exception as e:
        print("Error:", repr(e))
        print("Retrying in 5s...")
        await asyncio.sleep(5)
        await collect_once(out_file)

if __name__ == "__main__":
    if API_KEY in ("", "<YOUR_API_KEY>"):
        raise SystemExit("Please set AISSTREAM_API_KEY or fill API_KEY.")
    asyncio.run(main())
