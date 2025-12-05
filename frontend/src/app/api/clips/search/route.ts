import { NextRequest, NextResponse } from "next/server";

const DEFAULT_CLIPS_BASE_URL = "http://18.220.84.169:8000";

const CLIPS_BASE_URL =
  process.env.CLIPS_API_BASE_URL?.replace(/\/$/, "") ||
  DEFAULT_CLIPS_BASE_URL;

const SITE_VALUES = ["Bush_Point", "Orcasound_Lab", "Port_Townsend", "Sunset_Bay"];
const MAX_LOOKBACK_DAYS = 30;
const RECORDS_PER_SITE = 5;

type UpstreamClip = {
  site?: string | null;
  date_utc?: string | null;
  mmsi?: string | null;
  shipname?: string | null;
  t_cpa?: string | null;
  loudest_ts?: string | null;
  cpa_distance_m?: number | null;
  loudness_db?: number | null;
  aws_key?: string | null;
  record_url?: string | null;
  presigned_url?: string | null;
};

export const revalidate = 0;

const buildDateWindow = (baseDate: string, days: number): string[] => {
  const parsed = new Date(`${baseDate}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime()) || days <= 1) return [baseDate];
  return Array.from({ length: days }, (_, idx) => {
    const current = new Date(parsed.getTime());
    current.setUTCDate(parsed.getUTCDate() - idx);
    return current.toISOString().slice(0, 10);
  });
};

const normalizeNameForSearch = (value: string): string =>
  value.replace(/[_\s]+/g, " ").trim().toLowerCase();

const clipMatchesSearch = (clip: UpstreamClip, normalizedQuery: string): boolean => {
  if (!normalizedQuery) return true;
  const shipName = clip.shipname ?? "";
  const normalizedShipName = normalizeNameForSearch(shipName);
  const normalizedMmsi = normalizeNameForSearch(clip.mmsi ?? "");
  return (
    normalizedShipName.includes(normalizedQuery) ||
    normalizedMmsi.includes(normalizedQuery)
  );
};

type ClipSearchResponse = {
  start_date: string;
  end_date: string;
  lookback_days: number;
  limit_per_site: number;
  date_range_label: string;
  ship: string;
  results: UpstreamClip[];
};

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const shipQuery = searchParams.get("ship")?.trim();

  if (!shipQuery) {
    return NextResponse.json(
      { error: "`ship` query parameter is required" },
      { status: 400 },
    );
  }

  const normalizedQuery = normalizeNameForSearch(shipQuery);
  if (!normalizedQuery) {
    return NextResponse.json(
      { error: "`ship` query parameter must contain letters or numbers" },
      { status: 400 },
    );
  }

  const todayIso = new Date().toISOString().slice(0, 10);
  const candidateDates = buildDateWindow(todayIso, MAX_LOOKBACK_DAYS);
  const startDate = candidateDates.at(-1) ?? todayIso;

  const aggregated = await fetchAggregatedFromBackend(
    shipQuery,
    startDate,
    todayIso,
  );
  if (aggregated) {
    return NextResponse.json(aggregated);
  }

  const fallback = await fetchViaProxyFallback(
    normalizedQuery,
    shipQuery,
    candidateDates,
    startDate,
    todayIso,
  );
  if (fallback) {
    return NextResponse.json(fallback);
  }

  return NextResponse.json(
    { error: "Unable to load clips at this time" },
    { status: 502 },
  );
}

async function fetchAggregatedFromBackend(
  shipQuery: string,
  startDate: string,
  endDate: string,
): Promise<ClipSearchResponse | null> {
  const upstreamUrl = new URL("/clips/search", `${CLIPS_BASE_URL}/`);
  upstreamUrl.searchParams.set("shipname", shipQuery);
  upstreamUrl.searchParams.set("start_date", startDate);
  upstreamUrl.searchParams.set("end_date", endDate);
  upstreamUrl.searchParams.set("limit_per_site", `${RECORDS_PER_SITE}`);
  SITE_VALUES.forEach((site) =>
    upstreamUrl.searchParams.append("sites", site),
  );

  try {
    const response = await fetch(upstreamUrl, { cache: "no-store" });
    if (!response.ok) {
      console.warn(
        "[clips/search] Aggregated upstream request failed:",
        response.status,
      );
      return null;
    }

    const payload = await response.json();
    const results: UpstreamClip[] = Array.isArray(payload.results)
      ? payload.results
      : [];
    const startValue =
      typeof payload.start_date === "string" ? payload.start_date : startDate;
    const endValue =
      typeof payload.end_date === "string" ? payload.end_date : endDate;
    const rangeLabel =
      typeof payload.date_range_label === "string"
        ? payload.date_range_label
        : startValue === endValue
          ? startValue
          : `${startValue} – ${endValue}`;

    return {
      start_date: startValue,
      end_date: endValue,
      lookback_days: payload.lookback_days ?? MAX_LOOKBACK_DAYS,
      limit_per_site: payload.limit_per_site ?? RECORDS_PER_SITE,
      date_range_label: rangeLabel,
      ship: shipQuery,
      results,
    };
  } catch (error) {
    console.warn("[clips/search] Aggregated upstream request threw:", error);
    return null;
  }
}

async function fetchViaProxyFallback(
  normalizedQuery: string,
  shipQuery: string,
  candidateDates: string[],
  startDate: string,
  endDate: string,
): Promise<ClipSearchResponse | null> {
  const siteClipMap = new Map<string, UpstreamClip[]>();
  SITE_VALUES.forEach((site) => siteClipMap.set(site, []));

  let successfulFetches = 0;

  for (const dateValue of candidateDates) {
    const sitesNeedingData = SITE_VALUES.filter(
      (site) => (siteClipMap.get(site)?.length ?? 0) < RECORDS_PER_SITE,
    );

    if (sitesNeedingData.length === 0) {
      break;
    }

    await Promise.all(
      sitesNeedingData.map(async (siteValue) => {
        const upstreamUrl = new URL("/clips", `${CLIPS_BASE_URL}/`);
        upstreamUrl.searchParams.set("site", siteValue);
        upstreamUrl.searchParams.set("date", dateValue);
        upstreamUrl.searchParams.set("limit", "200");

        try {
          const upstreamResponse = await fetch(upstreamUrl, {
            cache: "no-store",
          });
          if (!upstreamResponse.ok) {
            const errorText = await upstreamResponse.text().catch(() => "");
            console.error(
              `[clips/search] Upstream ${siteValue} ${dateValue} failed with ${upstreamResponse.status}:`,
              errorText.slice(0, 200),
            );
            return;
          }

          const payload = await upstreamResponse.json();
          const dayClips: UpstreamClip[] = Array.isArray(payload.results)
            ? payload.results
            : [];
          if (!dayClips.length) {
            successfulFetches += 1;
            return;
          }

          const siteRecords = siteClipMap.get(siteValue);
          if (!siteRecords) return;

          for (const clip of dayClips) {
            if (siteRecords.length >= RECORDS_PER_SITE) break;
            if (!clipMatchesSearch(clip, normalizedQuery)) continue;
            siteRecords.push({
              ...clip,
              site: clip.site ?? siteValue,
              date_utc: clip.date_utc ?? dateValue,
            });
          }
          successfulFetches += 1;
        } catch (error) {
          console.error(
            `[clips/search] Failed to fetch ${siteValue} ${dateValue}:`,
            error,
          );
        }
      }),
    );
  }

  if (successfulFetches === 0) {
    return null;
  }

  const results = SITE_VALUES.flatMap((site) => siteClipMap.get(site) ?? []);
  const dateRangeLabel =
    startDate === endDate ? endDate : `${startDate} – ${endDate}`;

  return {
    start_date: startDate,
    end_date: endDate,
    lookback_days: MAX_LOOKBACK_DAYS,
    limit_per_site: RECORDS_PER_SITE,
    date_range_label: dateRangeLabel,
    ship: shipQuery,
    results,
  };
}
