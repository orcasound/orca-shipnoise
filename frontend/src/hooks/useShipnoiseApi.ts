import {
  keepPreviousData,
  useQuery,
} from '@tanstack/react-query';
import {
  fetchVesselSuggestions,
  fetchClipsSearch,
  fetchAisSite,
  normalizeNameForSearch,
  type VesselOption,
  type ClipsSearchParams,
  type ClipsSearchResponse,
  type AisSiteResponse,
} from '@/lib/api';

/**
 * Fetches vessel name suggestions for autocomplete.
 * Pass in already-debounced query string.
 */
export function useVesselSearch(query: string) {
  const normalized = normalizeNameForSearch(query);

  return useQuery<VesselOption[]>({
    queryKey: ['vessels', 'search', normalized],
    queryFn: ({ signal }) => fetchVesselSuggestions(normalized, signal),
    enabled: normalized.length > 0,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });
}

/**
 * Polls cached AIS vessel data for one hydrophone site. The backend enforces
 * the AISHub rate limit itself, so it's safe to poll this on a short interval
 * from as many mounted tiles as are on screen.
 */
export function useAisSite(slug: string) {
  return useQuery<AisSiteResponse>({
    queryKey: ['ais', 'site', slug],
    queryFn: ({ signal }) => fetchAisSite(slug, signal),
    placeholderData: keepPreviousData,
    staleTime: 20_000,
    refetchInterval: 30_000,
    retry: 1,
  });
}

/**
 * Searches for clip recordings. Manually triggered via `refetch()`.
 * Pass `enabled: false` by default; call `refetch()` on button click.
 */
export function useClipsSearch(params: ClipsSearchParams | null) {
  return useQuery<ClipsSearchResponse>({
    queryKey: ['clips', 'search', params],
    queryFn: ({ signal }) => {
      if (!params) throw new Error('No search params');
      return fetchClipsSearch(params, signal);
    },
    enabled: !!params,
    staleTime: 30_000,
    retry: 1,
  });
}
