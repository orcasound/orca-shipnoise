export type Site = {
  slug: string;
  name: string;
  lat: number;
  lon: number;
  /** S3 bucket + node name used to build the live HLS stream URL. */
  bucket: string;
  nodeName: string;
};

// Source: https://live.orcasound.net/api/json/feeds (visible: true)
// Ordered north to south so the grid reads geographically, top to bottom.
export const SITES: Site[] = [
  {
    slug: 'orcasound-lab',
    name: 'Orcasound Lab',
    lat: 48.5583,
    lon: -123.1736,
    bucket: 'audio-orcasound-net',
    nodeName: 'rpi_orcasound_lab',
  },
  {
    slug: 'andrews-bay',
    name: 'Andrews Bay',
    lat: 48.5467,
    lon: -123.1664,
    bucket: 'audio-orcasound-net',
    nodeName: 'rpi_andrews_bay',
  },
  {
    slug: 'north-sjc',
    name: 'North San Juan Channel',
    lat: 48.5913,
    lon: -123.0588,
    bucket: 'audio-orcasound-net',
    nodeName: 'rpi_north_sjc',
  },
  {
    slug: 'port-townsend',
    name: 'Port Townsend',
    lat: 48.1357,
    lon: -122.7606,
    bucket: 'audio-orcasound-net',
    nodeName: 'rpi_port_townsend',
  },
  {
    slug: 'bush-point',
    name: 'Bush Point',
    lat: 48.0337,
    lon: -122.604,
    bucket: 'audio-orcasound-net',
    nodeName: 'rpi_bush_point',
  },
  {
    slug: 'sunset-bay',
    name: 'Sunset Bay',
    lat: 47.865,
    lon: -122.3339,
    bucket: 'audio-orcasound-net',
    nodeName: 'rpi_sunset_bay',
  },
  {
    slug: 'mast-center',
    name: 'MaST Center Aquarium',
    lat: 47.3492,
    lon: -122.3251,
    bucket: 'audio-orcasound-net',
    nodeName: 'rpi_mast_center',
  },
];

export const SITES_BY_SLUG: Record<string, Site> = Object.fromEntries(
  SITES.map((site) => [site.slug, site]),
);
