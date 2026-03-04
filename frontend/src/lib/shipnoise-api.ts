import { useQuery, UseQueryResult } from '@tanstack/react-query';

const CLIPS_API_BASE_URL = process.env.NEXT_PUBLIC_CLIPS_API_BASE_URL?.replace(/\/$/, '');

const buildBackendUrl = (path: string, params: URLSearchParams): string => {
  if (!CLIPS_API_BASE_URL) {
    throw new Error('NEXT_PUBLIC_CLIPS_API_BASE_URL is not configured');
  }

  const url = new URL(path, `${CLIPS_API_BASE_URL}/`);
  for (const [key, value] of params.entries()) {
    url.searchParams.append(key, value);
  }
  return url.toString();
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
};

export type VesselSuggestion = {
  name: string;
};

export const fetchVesselSuggestions = async (
  rawQuery: string,
  limit = 20,
): Promise<VesselSuggestion[]> => {
  const normalizedQuery = rawQuery.trim().toLowerCase();
  if (!normalizedQuery.length) return [];

  const params = new URLSearchParams({
    q: normalizedQuery,
    limit: String(limit),
  });

  const url = buildBackendUrl('/vessels/search', params);
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Suggestion request failed with ${response.status}`);
  }

  const payload = await response.json();
  const names: string[] = Array.isArray(payload.results) ? payload.results : [];

  return names.map((name) => ({ name }));
};

export interface ClipsSearchParams {
  shipname: string;
  startDate: string;
  endDate: string;
  sites: string[];
  limitPerSite?: number;
}

export interface ClipsSearchResponse {
  results: ClipApiResult[];
  start_date?: string;
  end_date?: string;
  date_range_label?: string;
}

export const fetchClips = async (params: ClipsSearchParams): Promise<ClipsSearchResponse> => {
  const { shipname, startDate, endDate, sites, limitPerSite = 5 } = params;

  const searchParams = new URLSearchParams({
    shipname,
    start_date: startDate,
    end_date: endDate,
    limit_per_site: String(limitPerSite),
  });
  sites.forEach((site) => searchParams.append('sites', site));

  const url = buildBackendUrl('/clips/search', searchParams);
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Clip search failed with ${response.status}`);
  }

  const payload = await response.json();

  return {
    results: Array.isArray(payload.results) ? payload.results : [],
    start_date: typeof payload.start_date === 'string' ? payload.start_date : undefined,
    end_date: typeof payload.end_date === 'string' ? payload.end_date : undefined,
    date_range_label:
      typeof payload.date_range_label === 'string' ? payload.date_range_label : undefined,
  };
};

export const useVesselSuggestions = (
  query: string,
  limit = 20,
): UseQueryResult<VesselSuggestion[], Error> => {
  const normalizedQuery = query.trim().toLowerCase();

  return useQuery({
    queryKey: ['vesselSuggestions', normalizedQuery, limit],
    queryFn: () => fetchVesselSuggestions(normalizedQuery, limit),
    enabled: !!normalizedQuery.length && !!CLIPS_API_BASE_URL,
    staleTime: 60_000,
  });
};

export const useClipsSearch = (
  params: ClipsSearchParams | null,
  options?: { enabled?: boolean },
): UseQueryResult<ClipsSearchResponse, Error> => {
  const enabled = options?.enabled ?? true;

  return useQuery({
    queryKey: ['clipsSearch', params],
    queryFn: () => {
      if (!params) {
        throw new Error('Missing clips search parameters');
      }
      return fetchClips(params);
    },
    enabled: !!params && enabled && !!CLIPS_API_BASE_URL,
    staleTime: 0,
  });
};

