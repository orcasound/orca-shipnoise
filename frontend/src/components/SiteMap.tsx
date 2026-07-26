'use client';

import 'leaflet/dist/leaflet.css';
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet';
import type { AisVessel } from '@/lib/api';

export type SiteMapSite = {
  slug: string;
  name: string;
  lat: number;
  lon: number;
  radiusNm?: number;
};

interface SiteMapProps {
  site: SiteMapSite;
  vessels: AisVessel[];
  interactive?: boolean;
}

const OSM_TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const OSM_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

function formatKnots(sog: number | null): string {
  if (sog === null || Number.isNaN(sog)) return 'unknown speed';
  return `${sog.toFixed(1)} kn`;
}

export default function SiteMap({ site, vessels, interactive = true }: SiteMapProps) {
  const positionedVessels = vessels.filter(
    (v): v is AisVessel & { lat: number; lon: number } => v.lat !== null && v.lon !== null,
  );

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
