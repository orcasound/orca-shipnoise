"""
Rate-limited AIS vessel-position service for the hydrophone sites.

AISHub allows at most one request per minute across the whole account, and
that limit applies globally -- not per site. To keep every site reasonably
fresh under that constraint, a single background loop round-robins through
all sites, spaced exactly 60s apart. When a site is requested through the
API and its cached data is stale, it gets bumped to the front of the queue
so it refreshes on the next tick instead of waiting for its round-robin
turn.
"""

import asyncio
import bz2
import json
import logging
import math
import os
import time
from collections import deque
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional

import requests

logger = logging.getLogger("ais_service")

AISHUB_URL = "https://data.aishub.net/ws.php"
AISHUB_MIN_INTERVAL_SEC = 60
STALE_THRESHOLD_SEC = 90

NM_PER_DEG_LAT = 60.0


@dataclass(frozen=True)
class Site:
    slug: str
    name: str
    lat: float
    lon: float
    radius_nm: float = 5.0


# Coordinates match live.orcasound.net/api/json/feeds (visible: true) and
# the site list used by the frontend's /ais-maps page.
SITES: list[Site] = [
    Site("north-sjc", "North San Juan Channel", 48.5913, -123.0588),
    Site("orcasound-lab", "Orcasound Lab", 48.5583, -123.1736),
    Site("andrews-bay", "Andrews Bay", 48.5467, -123.1664),
    Site("port-townsend", "Port Townsend", 48.1357, -122.7606),
    Site("bush-point", "Bush Point", 48.0337, -122.604),
    Site("sunset-bay", "Sunset Bay", 47.865, -122.3339),
    Site("mast-center", "MaST Center Aquarium", 47.3492, -122.3251),
]
SITES_BY_SLUG: dict[str, Site] = {s.slug: s for s in SITES}


def _bounding_box(lat: float, lon: float, radius_nm: float) -> tuple[float, float, float, float]:
    lat_delta = radius_nm / NM_PER_DEG_LAT
    lon_delta = radius_nm / (NM_PER_DEG_LAT * math.cos(math.radians(lat)))
    return lat - lat_delta, lat + lat_delta, lon - lon_delta, lon + lon_delta


def _fetch_boats_in_area(
    username: str, latmin: float, latmax: float, lonmin: float, lonmax: float
) -> list[dict]:
    params = {
        "username": username,
        "format": 1,
        "output": "json",
        "compress": 3,
        "latmin": latmin,
        "latmax": latmax,
        "lonmin": lonmin,
        "lonmax": lonmax,
    }
    response = requests.get(AISHUB_URL, params=params, timeout=30)
    response.raise_for_status()

    content = response.content
    if content[:3] == b"BZh":  # bzip2 magic bytes
        content = bz2.decompress(content)

    data = json.loads(content)

    meta = data[0]
    if meta.get("ERROR"):
        raise RuntimeError(f"AISHub API error: {meta}")

    return data[1] if len(data) > 1 else []


def _to_vessel(raw: dict) -> dict:
    return {
        "mmsi": raw.get("MMSI"),
        "name": (raw.get("NAME") or "").strip() or None,
        "lat": raw.get("LATITUDE"),
        "lon": raw.get("LONGITUDE"),
        "sog": raw.get("SOG"),
        "cog": raw.get("COG"),
        "type": raw.get("TYPE"),
        "navstat": raw.get("NAVSTAT"),
        "time": raw.get("TIME"),
    }


@dataclass
class SiteCacheEntry:
    vessels: list[dict] = field(default_factory=list)
    updated_at: Optional[str] = None  # ISO 8601 UTC, for API clients
    fetched_at_monotonic: Optional[float] = None  # for internal staleness checks only
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "vessels": self.vessels,
            "updated_at": self.updated_at,
            "error": self.error,
        }


class AisPoller:
    """Owns the single global AISHub rate limit and the per-site cache."""

    def __init__(self, username: Optional[str], sites: list[Site] = SITES):
        self.username = username
        self.sites = sites
        self.cache: dict[str, SiteCacheEntry] = {s.slug: SiteCacheEntry() for s in sites}
        self._round_robin: deque[str] = deque(s.slug for s in sites)
        self._priority: deque[str] = deque()
        self._last_call_at: Optional[float] = None
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None

    def request_refresh(self, slug: str) -> None:
        """Bump a site to the front of the queue if its data is missing or stale."""
        entry = self.cache.get(slug)
        if entry is None:
            return
        is_stale = (
            entry.fetched_at_monotonic is None
            or (time.monotonic() - entry.fetched_at_monotonic) > STALE_THRESHOLD_SEC
        )
        if is_stale and slug not in self._priority:
            self._priority.append(slug)

    def get(self, slug: str) -> Optional[SiteCacheEntry]:
        return self.cache.get(slug)

    async def _run(self) -> None:
        if not self.username:
            logger.warning("AISHUB_USERNAME not set; AIS polling loop will not start.")
            return

        while True:
            await self._respect_rate_limit()

            slug = self._priority.popleft() if self._priority else self._round_robin.popleft()
            # Whether slug came from the priority queue or its round-robin turn,
            # move it to the back of the rotation so it isn't polled again early.
            if slug in self._round_robin:
                self._round_robin.remove(slug)
            self._round_robin.append(slug)

            self._last_call_at = time.monotonic()
            await self._poll_site(slug)

    async def _respect_rate_limit(self) -> None:
        if self._last_call_at is None:
            return
        elapsed = time.monotonic() - self._last_call_at
        remaining = AISHUB_MIN_INTERVAL_SEC - elapsed
        if remaining > 0:
            await asyncio.sleep(remaining)

    async def _poll_site(self, slug: str) -> None:
        site = SITES_BY_SLUG[slug]
        latmin, latmax, lonmin, lonmax = _bounding_box(site.lat, site.lon, site.radius_nm)
        try:
            raw_boats = await asyncio.to_thread(
                _fetch_boats_in_area, self.username, latmin, latmax, lonmin, lonmax
            )
            vessels = [_to_vessel(b) for b in raw_boats]
            self.cache[slug] = SiteCacheEntry(
                vessels=vessels,
                updated_at=datetime.now(timezone.utc).isoformat(),
                fetched_at_monotonic=time.monotonic(),
            )
            logger.info("AIS refresh ok for %s: %d vessels", slug, len(vessels))
        except Exception as exc:  # noqa: BLE001 - keep the loop alive on any failure
            logger.warning("AIS refresh failed for %s: %s", slug, exc)
            previous = self.cache.get(slug, SiteCacheEntry())
            self.cache[slug] = SiteCacheEntry(
                vessels=previous.vessels,
                updated_at=previous.updated_at,
                fetched_at_monotonic=previous.fetched_at_monotonic,
                error=str(exc),
            )


ais_poller = AisPoller(username=os.getenv("AISHUB_USERNAME"))
