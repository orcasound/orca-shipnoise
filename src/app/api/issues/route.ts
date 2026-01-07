import { NextResponse } from "next/server";

const SHEET_API_URL =
  "https://script.google.com/macros/s/AKfycbx6kn3zYIzmLLVXEAhJxW7jna-QsRwSJgvSIZvvaQOz9gvnC97tdgeXuL0MtzvET_qD/exec";

export const revalidate = 0;

export async function GET() {
  try {
    const response = await fetch(SHEET_API_URL, {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`Upstream request failed with ${response.status}`);
    }

    const rawBody = await response.text();

    try {
      const sanitized = rawBody.replace(/^\)\]\}'/, "").trim();
      if (!sanitized.trim()) {
        return NextResponse.json({ data: [] }, { status: 200 });
      }
      const parsed = JSON.parse(sanitized);
      return NextResponse.json(parsed, { status: 200 });
    } catch (parseError) {
      console.error("Upstream returned non-JSON payload:", parseError);
      return NextResponse.json(
        {
          error: "Upstream response was not valid JSON",
          debug: rawBody.slice(0, 120),
        },
        { status: 502 },
      );
    }
  } catch (error) {
    console.error("Failed to fetch Sheet data:", error);
    return NextResponse.json(
      { error: "Failed to fetch Sheet data" },
      { status: 500 },
    );
  }
}
