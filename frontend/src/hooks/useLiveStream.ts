import { useQuery } from '@tanstack/react-query';

const getBucketBase = (bucket: string) => `https://${bucket}.s3.amazonaws.com`;

const getHlsUrl = (bucket: string, nodeName: string, timestamp: string) =>
  `${getBucketBase(bucket)}/${nodeName}/hls/${timestamp}/live.m3u8`;

async function fetchLiveHlsUrl(
  bucket: string,
  nodeName: string,
  signal?: AbortSignal,
): Promise<string> {
  const response = await fetch(`${getBucketBase(bucket)}/${nodeName}/latest.txt`, { signal });
  if (!response.ok) throw new Error(`latest.txt request failed with ${response.status}`);
  const timestamp = (await response.text()).trim();
  return getHlsUrl(bucket, nodeName, timestamp);
}

/**
 * Polls for the current live HLS stream URL for a hydrophone node, mirroring
 * orcasite's own polling cadence (every 10s) since the stream's underlying
 * S3 folder rotates periodically.
 */
export function useLiveStreamUrl(bucket?: string, nodeName?: string) {
  return useQuery<string>({
    queryKey: ['live-stream', bucket, nodeName],
    queryFn: ({ signal }) => {
      if (!bucket || !nodeName) throw new Error('bucket and nodeName are required');
      return fetchLiveHlsUrl(bucket, nodeName, signal);
    },
    enabled: !!bucket && !!nodeName,
    refetchInterval: 10_000,
    staleTime: 8_000,
    retry: 1,
  });
}
