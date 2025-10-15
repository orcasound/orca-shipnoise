# ais_collect.py
import os, json, math, asyncio, websockets
from datetime import datetime, timezone, timedelta

# === REQUIRED: Your AISstream API Key ===
API_KEY = os.getenv("AISSTREAM_API_KEY")
if not API_KEY:
    raise SystemExit("Please set AISSTREAM_API_KEY environment variable.")

# === Hydrophone coordinates (example: Port Townsend Marine Science Center) ===
HYDRO_LAT, HYDRO_LON = 48.1358, -122.7596

# === Bounding box radius (km) ===
R_KM = 30.0

# === Duration of data collection in seconds (e.g., 1800=30min, 3600=1h) ===
DURATION_SECS = 3600


# --- Convert radius in km to a bounding box ---
def bbox_from_radius_km(lat, lon, r_km):
    dlat = r_km / 111.0
    dlon = r_km / (111.0 * max(0.1, math.cos(math.radians(lat))))
    return [[lat - dlat, lon - dlon], [lat + dlat, lon + dlon]]


# --- Main collector ---
async def collect_once(out_path: str):
    uri = "wss://stream.aisstream.io/v0/stream"
    bbox = bbox_from_radius_km(HYDRO_LAT, HYDRO_LON, R_KM)

    # === Create date folder automatically (e.g., data/20251010/) ===
    now = datetime.now(timezone.utc)
    date_folder = now.strftime("%Y%m%d")
    base_dir = "/home/ubuntu/aisstream/data"
    os.makedirs(os.path.join(base_dir, date_folder), exist_ok=True)

    # === Output file path ===
    out_path = os.path.join(
        base_dir,
        date_folder,
        f"ais_raw_{now.strftime('%Y%m%dT%H%M%SZ')}.jsonl"
    )

    sub_msg = {
        "APIKey": API_KEY,
        "BoundingBoxes": [bbox],
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
                if isinstance(msg, (bytes, bytearray)):
                    msg = msg.decode("utf-8", errors="ignore")
                f.write(msg.strip() + "\n")
                cnt += 1
                if cnt % 200 == 0:
                    print(f"[{now.isoformat()}] received {cnt} messages...")
        print(f"Saved: {out_path}  (messages={cnt})")


# --- Entry point ---
async def main():
    try:
        await collect_once("placeholder.jsonl")
    except Exception as e:
        print("Error:", repr(e))
        print("Retrying in 5s...")
        await asyncio.sleep(5)
        await collect_once("placeholder.jsonl")


if __name__ == "__main__":
    if API_KEY in ("", "<YOUR_API_KEY>"):
        raise SystemExit("Please set AISSTREAM_API_KEY or fill API_KEY.")
    asyncio.run(main())


