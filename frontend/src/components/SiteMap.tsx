'use client';

import 'leaflet/dist/leaflet.css';
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer } from 'react-leaflet';
import type { AisVessel } from '@/lib/api';
import type { Site } from '@/lib/sites';

interface SiteMapProps {
  site: Pick<Site, 'slug' | 'name' | 'lat' | 'lon'>;
  vessels: AisVessel[];
  interactive?: boolean;
}

const OSM_TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const OSM_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

const NM_PER_DEG_LAT = 60.0;
// How far ahead each vessel's speed vector projects, matching the local
// plot_boats.py prototype's default.
const VECTOR_MINUTES = 10;

function formatKnots(sog: number | null): string {
  if (sog === null || Number.isNaN(sog)) return 'unknown speed';
  return `${sog.toFixed(1)} kn`;
}

/** Projects a vessel's position forward along its course, given its speed
 * (knots) and course over ground (degrees). Ported from plot_boats.py's
 * speed_vector_endpoint. */
function projectPosition(
  lat: number,
  lon: number,
  cog: number,
  sog: number,
  minutes: number,
): [number, number] {
  const distanceNm = sog * (minutes / 60);
  const angle = (cog * Math.PI) / 180;
  const dlat = (distanceNm / NM_PER_DEG_LAT) * Math.cos(angle);
  const dlon = (distanceNm / (NM_PER_DEG_LAT * Math.cos((lat * Math.PI) / 180))) * Math.sin(angle);
  return [lat + dlat, lon + dlon];
}

export default function SiteMap({ site, vessels, interactive = true }: SiteMapProps) {
  const positionedVessels = vessels.filter(
    (v): v is AisVessel & { lat: number; lon: number } => v.lat !== null && v.lon !== null,
  );

  // COG 360 is the AIS sentinel for "not available" -- valid courses are [0, 360).
  const hasValidCourse = (cog: number | null): cog is number =>
    cog !== null && cog >= 0 && cog < 360;

  return (
    <MapContainer
      center={[site.lat, site.lon]}
      zoom={11}
      scrollWheelZoom={false}
      dragging={interactive}
      doubleClickZoom={interactive}
      zoomControl={interactive}
      touchZoom={interactive}
      style={{ height: '100%', width: '100%' }}
    >
      <TileLayer url={OSM_TILE_URL} attribution={OSM_ATTRIBUTION} />

      <CircleMarker
        center={[site.lat, site.lon]}
        radius={7}
        pathOptions={{ color: '#1d4ed8', fillColor: '#1d4ed8', fillOpacity: 0.9 }}
      >
        <Popup>{site.name} (hydrophone)</Popup>
      </CircleMarker>

      {positionedVessels
        .filter((vessel) => (vessel.sog ?? 0) > 0 && hasValidCourse(vessel.cog))
        .map((vessel) => (
          <Polyline
            key={`vector-${vessel.mmsi ?? `${vessel.lat},${vessel.lon}`}`}
            positions={[
              [vessel.lat, vessel.lon],
              projectPosition(vessel.lat, vessel.lon, vessel.cog as number, vessel.sog as number, VECTOR_MINUTES),
            ]}
            pathOptions={{ color: '#16a34a', weight: 2 }}
          />
        ))}

      {positionedVessels.map((vessel) => (
        <CircleMarker
          key={vessel.mmsi ?? `${vessel.lat},${vessel.lon}`}
          center={[vessel.lat, vessel.lon]}
          radius={4}
          pathOptions={{ color: '#dc2626', fillColor: '#dc2626', fillOpacity: 0.85 }}
        >
          <Popup>
            <strong>{vessel.name ?? 'Unknown vessel'}</strong>
            <br />
            {formatKnots(vessel.sog)}
            {vessel.mmsi ? (
              <>
                <br />
                MMSI {vessel.mmsi}
              </>
            ) : null}
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
