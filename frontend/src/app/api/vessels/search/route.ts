import { NextRequest, NextResponse } from "next/server";

const DEFAULT_BACKEND_BASE_URL = "https://orca-shipnoise.fly.dev";
const BACKEND_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  DEFAULT_BACKEND_BASE_URL;

export const revalidate = 0;

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const query = searchParams.get("q");
  const limit = searchParams.get("limit") ?? "20";

  if (!query || !query.trim()) {
    return NextResponse.json({ count: 0, results: [] });
  }

  const upstreamUrl = new URL("/vessels/search", `${BACKEND_BASE_URL}/`);
  upstreamUrl.searchParams.set("q", query);
  upstreamUrl.searchParams.set("limit", limit);

  try {
    const upstreamResponse = await fetch(upstreamUrl, {
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      const errorText = await upstreamResponse.text().catch(() => "");
      console.error(
        `Vessel search API responded with ${upstreamResponse.status}:`,
        errorText.slice(0, 200),
      );
      return NextResponse.json(
        { error: "Failed to fetch vessel names from upstream service" },
        { status: upstreamResponse.status },
      );
    }

    const upstreamPayload = await upstreamResponse.json();
    const results: string[] = Array.isArray(upstreamPayload.results)
      ? upstreamPayload.results
      : [];

    return NextResponse.json({
      ...upstreamPayload,
      count: upstreamPayload.count ?? results.length,
      results,
    });
  } catch (error) {
    console.error("Unexpected error calling vessel search API:", error);
    return NextResponse.json(
      { error: "Unable to reach vessel search service" },
      { status: 502 },
    );
  }
}
