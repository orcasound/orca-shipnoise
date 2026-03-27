import os, json, math, asyncio, websockets, argparse, requests, statistics
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
import sys
from config.sites import ORCASITE_GRAPHQL, AISSTREAM_WS

load_dotenv()

# ============ CONFIG ============
MAX_RETRIES = 5

# ============ ENV ============
API_KEY = os.getenv("AISSTREAM_API_KEY")
if not API_KEY:
    raise SystemExit("Please set AISSTREAM_API_KEY environment variable.")

# ============ CLI ============
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--sites", required=True, nargs="+", help="Site slugs, e.g. bush-point orcasound-lab")
    p.add_argument(
        "--duration",
        type=int,
        default=3600,
        help="Collection duration in seconds (default: 3600)",
    )
    p.add_argument(
        "--radius",
        type=float,
        default=30.0,
        help="Collection radius in km (default: 30.0)",
    )
    return p.parse_args()

# ============ ORCASITE ============
def get_all_site_locations(site_slugs: list):
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

    locations = {}
    for feed in data["data"]["feeds"]:
        if feed["slug"] in site_slugs:
            lp = feed["location_point"]
            if isinstance(lp, str):
                lp = json.loads(lp)
            lon, lat = lp["coordinates"]
            locations[feed["slug"]] = (lat, lon)

    missing = set(site_slugs) - set(locations.keys())
    if missing:
        raise ValueError(f"Unknown site slugs: {missing}")
    return locations

# ============ PATHS ============
PROJECT_ROOT = Path(__file__).resolve().parents[2]

def get_base_dir(site_slug: str):
    base = PROJECT_ROOT / "Sites" / f"{site_slug.replace('-', '_')}_data"
    base.mkdir(parents=True, exist_ok=True)
    return base

def make_out_file(base_dir: Path) -> Path:
    now = datetime.now(timezone.utc)
    out_dir = base_dir / now.strftime("%Y%m%d")
    out_dir.mkdir(exist_ok=True)
    return out_dir / f"ais_raw_{now.strftime('%Y%m%dT%H%M%SZ')}.jsonl"

# ============ GEO ============
def bbox_from_radius_km(lat, lon, r_km):
    dlat = r_km / 111.0
    dlon = r_km / (111.0 * max(0.1, math.cos(math.radians(lat))))
    return [[lat - dlat, lon - dlon], [lat + dlat, lon + dlon]]

def point_in_bbox(lat, lon, bbox):
    return (bbox[0][0] <= lat <= bbox[1][0] and
            bbox[0][1] <= lon <= bbox[1][1])

# ============ BASELINE / ANOMALY DETECTION ============
def compute_baseline(site_slugs: list) -> dict:
    """Scan historical .jsonl files to compute per-site message count statistics."""
    baselines = {}
    for site in site_slugs:
        base_dir = get_base_dir(site)
        counts = []
        for path in sorted(base_dir.rglob("ais_raw_*.jsonl")):
            try:
                with path.open() as f:
                    n = sum(1 for _ in f) - 1  # subtract _meta header line
                if n > 0:
                    counts.append(n)
            except Exception:
                pass
        if len(counts) >= 3:
            mean = statistics.mean(counts)
            stdev = statistics.stdev(counts)
            baselines[site] = {"mean": mean, "stdev": stdev, "n": len(counts)}
    return baselines


def check_anomalies(site_data: dict, baselines: dict):
    """Print baseline comparison and warn if any site count looks unusually low."""
    for site, info in site_data.items():
        count = info["count"]
        if site not in baselines:
            print(f"[baseline] site={site} count={count} status=NO_HISTORY")
            continue
        b = baselines[site]
        threshold = max(0, b["mean"] - 2 * b["stdev"])
        status = "LOW" if count < threshold else "OK"
        print(
            f"[baseline] site={site} count={count} mean={b['mean']:.0f} "
            f"stdev={b['stdev']:.0f} threshold={threshold:.0f} status={status}"
        )
        if status == "LOW":
            print(
                f"[anomaly] WARNING site={site}: {count} msgs below threshold {threshold:.0f} "
                f"(mean={b['mean']:.0f}±{b['stdev']:.0f}, n={b['n']})"
            )

# ============ COLLECT ============
async def collect_once(sites_info: dict, duration_secs: int, radius_km: float):
    """
    sites_info: {site_slug: (lat, lon)}
    Single WebSocket connection subscribing to all site bboxes at once.
    Messages are routed to the correct site output file by position.
    """
    start = datetime.now(timezone.utc)
    deadline = start + timedelta(seconds=duration_secs)

    # Build per-site metadata
    site_data = {}
    all_bboxes = []
    for site, (lat, lon) in sites_info.items():
        bbox = bbox_from_radius_km(lat, lon, radius_km)
        out_path = make_out_file(get_base_dir(site))
        site_data[site] = {
            "lat": lat, "lon": lon,
            "bbox": bbox,
            "out_path": out_path,
            "count": 0,
        }
        all_bboxes.append(bbox)

    sub_msg = {
        "APIKey": API_KEY,
        "BoundingBoxes": all_bboxes,
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
    }

    print(f"Connecting... {AISSTREAM_WS}  sites={list(sites_info.keys())}")

    # Open all output files and write metadata headers
    file_handles = {}
    for site, info in site_data.items():
        f = open(info["out_path"], "w", encoding="utf-8")
        f.write(json.dumps({"_meta": {
            "site": site,
            "latitude": info["lat"],
            "longitude": info["lon"],
            "radius_km": radius_km,
            "started_at": start.isoformat(),
        }}) + "\n")
        file_handles[site] = f

    try:
        async with websockets.connect(
            AISSTREAM_WS,
            open_timeout=60,
            ping_timeout=120,
            close_timeout=10,
            max_size=2**20,
        ) as ws:
            await ws.send(json.dumps(sub_msg))
            print("Subscription sent. Waiting for data...")

            total_cnt = 0
            async for msg in ws:
                if datetime.now(timezone.utc) >= deadline:
                    break
                if isinstance(msg, (bytes, bytearray)):
                    msg = msg.decode("utf-8", errors="ignore")

                # Route message to matching site(s) by position
                try:
                    parsed = json.loads(msg)
                    meta = parsed.get("MetaData", {})
                    msg_lat = meta.get("latitude") or meta.get("Latitude")
                    msg_lon = meta.get("longitude") or meta.get("Longitude")
                except (json.JSONDecodeError, AttributeError):
                    msg_lat = msg_lon = None

                if msg_lat is not None and msg_lon is not None:
                    for site, info in site_data.items():
                        if point_in_bbox(msg_lat, msg_lon, info["bbox"]):
                            file_handles[site].write(msg.strip() + "\n")
                            site_data[site]["count"] += 1

                total_cnt += 1
                if total_cnt % 200 == 0:
                    counts = {s: site_data[s]["count"] for s in site_data}
                    print(f"[{datetime.now(timezone.utc).isoformat()}] received {total_cnt} total | per-site: {counts}")
    finally:
        for site, f in file_handles.items():
            f.close()
            count = site_data[site]["count"]
            path = site_data[site]["out_path"]
            if count == 0:
                path.unlink(missing_ok=True)
                print(f"Removed empty file: {path}")
            else:
                print(f"Saved: {path}  (messages={count})")

        # Anomaly detection: compare counts to historical baseline
        baselines = compute_baseline(list(site_data.keys()))
        check_anomalies(site_data, baselines)

# ============ MAIN ============
async def main():
    args = parse_args()
    sites = args.sites
    duration = max(1, int(args.duration))
    radius = float(args.radius)

    print(f"Fetching locations for: {sites}")
    sites_info = get_all_site_locations(sites)
    for site, (lat, lon) in sites_info.items():
        print(f"  {site}: lat={lat}, lon={lon}")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[multi-site] Attempt {attempt}/{MAX_RETRIES} (duration={duration}s, radius={radius}km)")
            await collect_once(sites_info, duration, radius)
            return
        except TimeoutError as e:
            wait = min(30 * (2 ** (attempt - 1)), 120)
            print(f"[multi-site] Timeout on attempt {attempt}: {e}")
            print(f"[multi-site] Waiting {wait}s before retry...")
            await asyncio.sleep(wait)
        except Exception as e:
            wait = min(30 * (2 ** (attempt - 1)), 120)
            print(f"[multi-site] Error on attempt {attempt}: {repr(e)}")
            print(f"[multi-site] Waiting {wait}s before retry...")
            await asyncio.sleep(wait)

    print(f"[multi-site] All {MAX_RETRIES} attempts failed. Exiting.")

if __name__ == "__main__":
    asyncio.run(main())
