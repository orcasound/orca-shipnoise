import os, json, math, asyncio, websockets, argparse, requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()


# ============ CONFIG ============
ORCASITE_GRAPHQL = "https://live.orcasound.net/graphql"
AISSTREAM_WS = "wss://stream.aisstream.io/v0/stream"

# ============ ENV ============
API_KEY = os.getenv("AISSTREAM_API_KEY")
if not API_KEY:
    raise SystemExit("Please set AISSTREAM_API_KEY environment variable.")

# ============ CLI ============
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--site", required=True, help="Site slug, e.g. bush-point")
    p.add_argument("--radius-km", type=float, default=30.0)
    return p.parse_args()

# ============ ORCASITE ============
def get_site_latlon(site_slug: str):
    query = """
    query {
      feeds {
        slug
        location_point
      }
    }
    """
    r = requests.post(ORCASITE_GRAPHQL, json={"query": query}, timeout=10)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])

    for feed in data["data"]["feeds"]:
        if feed["slug"] == site_slug:
            lp = feed["location_point"]
            if isinstance(lp, str):
                lp = json.loads(lp)
            lon, lat = lp["coordinates"]
            return lat, lon

    raise ValueError(f"Unknown site slug: {site_slug}")

# ============ DURATION ============
def resolve_duration(default: int = 3600) -> int:
    raw = os.getenv("AIS_DURATION_SECS", "")
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        print(f"Invalid AIS_DURATION_SECS={raw!r}; falling back to {default}")
        return default

DURATION_SECS = resolve_duration()

# ============ PATHS ============
PROJECT_ROOT = Path(__file__).resolve().parents[2]

def get_base_dir(site_slug: str):
    base = PROJECT_ROOT / "Sites" / f"{site_slug.replace('-', '_')}_data"
    base.mkdir(parents=True, exist_ok=True)
    return base

# ============ GEO ============
def bbox_from_radius_km(lat, lon, r_km):
    dlat = r_km / 111.0
    dlon = r_km / (111.0 * max(0.1, math.cos(math.radians(lat))))
    return [[lat - dlat, lon - dlon], [lat + dlat, lon + dlon]]

# ============ COLLECT ============
async def collect_once(out_path: Path, lat: float, lon: float, r_km: float, site: str):
    bbox = bbox_from_radius_km(lat, lon, r_km)
    sub_msg = {
        "APIKey": API_KEY,
        "BoundingBoxes": [bbox],
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
    }

    print(f"Connecting... {AISSTREAM_WS}  BBOX={bbox}")
    start = datetime.now(timezone.utc)
    deadline = start + timedelta(seconds=DURATION_SECS)

    async with websockets.connect(AISSTREAM_WS) as ws:
        await ws.send(json.dumps(sub_msg))
        print("Subscription sent. Waiting for data...")

        cnt = 0
        with open(out_path, "w", encoding="utf-8") as f:
            meta = {"_meta": {"site": site, "latitude": lat, "longitude": lon, "radius_km": r_km}}
            f.write(json.dumps(meta) + "\n")

            async for msg in ws:
                if datetime.now(timezone.utc) >= deadline:
                    break
                if isinstance(msg, (bytes, bytearray)):
                    msg = msg.decode("utf-8", errors="ignore")
                f.write(msg.strip() + "\n")
                cnt += 1
                if cnt % 200 == 0:
                    print(f"[{datetime.now(timezone.utc).isoformat()}] received {cnt} messages...")

        print(f"Saved: {out_path}  (messages={cnt})")

# ============ MAIN ============
async def main():
    args = parse_args()
    site = args.site
    r_km = args.radius_km

    lat, lon = get_site_latlon(site)
    print(f"Site {site}: lat={lat}, lon={lon}")

    base_dir = get_base_dir(site)

    now = datetime.now(timezone.utc)
    out_dir = base_dir / now.strftime("%Y%m%d")
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"ais_raw_{now.strftime('%Y%m%dT%H%M%SZ')}.jsonl"

    try:
        await collect_once(out_file, lat, lon, r_km, site)
    except Exception as e:
        print("Error:", repr(e))
        print("Retrying in 5s...")
        await asyncio.sleep(5)
        await collect_once(out_file, lat, lon, r_km, site)

if __name__ == "__main__":
    asyncio.run(main())
