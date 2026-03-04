export type VesselOption = {
  name: string;
};

export type ClipApiResult = {
  site: string;
  date_utc?: string;
  mmsi?: string | null;
  shipname?: string | null;
  audio_urls?: string[] | null;
  cpa_distance_m?: number | null;
  t_cpa?: string | null;
  center_segment_index?: number;
  // HLS playback fields (derived from segment_details on the backend)
  hls_url?: string | null;
  start_offset_sec?: number | null;
  end_offset_sec?: number | null;
};

export type ClipsSearchResponse = {
  count: number;
  start_date?: string;
  end_date?: string;
  date_range_label?: string;
  shipname_query?: string;
  sites?: string[];
  limit_per_site?: number;
  results: ClipApiResult[];
};

export type VesselSearchResponse = {
  results: string[];
};

export const SITE_LABELS: Record<string, string> = {
  bush_point: 'Bush Point',
  orcasound_lab: 'Orcasound Lab',
  port_townsend: 'Port Townsend',
  sunset_bay: 'Sunset Bay',
};

export const SITE_VALUES = Object.keys(SITE_LABELS);

export const SITE_OPTIONS = Object.entries(SITE_LABELS).map(([value, label]) => ({
  value,
  label,
}));

const CLIPS_API_BASE_URL = process.env.NEXT_PUBLIC_CLIPS_API_BASE_URL?.replace(/\/$/, '');

export const buildBackendUrl = (path: string, params: URLSearchParams): string | null => {
  if (!CLIPS_API_BASE_URL) return null;
  const url = new URL(path, `${CLIPS_API_BASE_URL}/`);
  for (const [key, value] of params.entries()) {
    url.searchParams.append(key, value);
  }
  return url.toString();
};

export const formatShipName = (value?: string | null): string | undefined => {
  if (!value) return undefined;
  const cleaned = value.replace(/[_\s]+/g, ' ').trim();
  if (!cleaned) return undefined;
  return cleaned
    .split(' ')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
    .join(' ');
};

export const normalizeNameForSearch = (value: string): string =>
  value.replace(/[_\s]+/g, ' ').trim().toLowerCase();

export const formatTitleCase = (value: string): string =>
  value
    .split(' ')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
    .join(' ');

export async function fetchVesselSuggestions(
  query: string,
  signal?: AbortSignal,
): Promise<VesselOption[]> {
  const params = new URLSearchParams({ q: query, limit: '20' });
  const url = buildBackendUrl('/vessels/search', params);
  if (!url) throw new Error('NEXT_PUBLIC_CLIPS_API_BASE_URL is not configured');

  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error(`Suggestion request failed with ${response.status}`);

  const payload: VesselSearchResponse = await response.json();
  const names = Array.isArray(payload.results) ? payload.results : [];
  return names.map((name) => ({ name: formatShipName(name) ?? name }));
}

export interface ClipsSearchParams {
  shipname: string;
  startDate: string;
  endDate: string;
  sites?: string[];
  limitPerSite?: number;
}

export async function fetchClipsSearch(
  params: ClipsSearchParams,
  signal?: AbortSignal,
): Promise<ClipsSearchResponse> {
  const searchParams = new URLSearchParams({
    shipname: params.shipname,
    start_date: params.startDate,
    end_date: params.endDate,
    limit_per_site: String(params.limitPerSite ?? 5),
  });
  (params.sites ?? SITE_VALUES).forEach((site) => searchParams.append('sites', site));

  const url = buildBackendUrl('/clips/search', searchParams);
  if (!url) throw new Error('NEXT_PUBLIC_CLIPS_API_BASE_URL is not configured');

  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error(`Clip search failed with ${response.status}`);

  return response.json();
}
