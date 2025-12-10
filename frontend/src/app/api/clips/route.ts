import { NextRequest, NextResponse } from "next/server";

const DEFAULT_CLIPS_BASE_URL = "https://orca-shipnoise.fly.dev";
const CLIPS_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  DEFAULT_CLIPS_BASE_URL;

type UpstreamClip = {
  site: string;
  date_utc: string;
  mmsi: string;
  shipname: string;
  cpa_distance_m: number;
  loudness_db: number;
  aws_key?: string;
  presigned_url?: string | null;
};

export const revalidate = 0;

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const site = searchParams.get("site");
  const date = searchParams.get("date");
  const limit = searchParams.get("limit") ?? "20";

  if (!site || !date) {
    return NextResponse.json(
      { error: "`site` and `date` query parameters are required" },
      { status: 400 },
    );
  }

  const upstreamUrl = new URL("/clips", `${CLIPS_BASE_URL}/`);
  upstreamUrl.searchParams.set("site", site);
  upstreamUrl.searchParams.set("date", date);
  upstreamUrl.searchParams.set("limit", limit);

  try {
    console.info(
      "[/api/clips] fetching upstream:",
      `${upstreamUrl.pathname}?${upstreamUrl.searchParams.toString()}`,
    );
    const upstreamResponse = await fetch(upstreamUrl, {
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      const errorText = await upstreamResponse.text().catch(() => "");
      console.error(
        `Clips API responded with ${upstreamResponse.status}:`,
        errorText.slice(0, 200),
      );
      return NextResponse.json(
        { error: "Failed to fetch clips from upstream service" },
        { status: upstreamResponse.status },
      );
    }

    const upstreamPayload = await upstreamResponse.json();
    const results: UpstreamClip[] = Array.isArray(upstreamPayload.results)
      ? upstreamPayload.results
      : [];

    return NextResponse.json({
      ...upstreamPayload,
      count: upstreamPayload.count ?? results.length,
      results,
    });
  } catch (error) {
    console.error("Unexpected error calling clips API:", error);
    return NextResponse.json(
      { error: "Unable to reach clips service" },
      { status: 502 },
    );
  }
}
