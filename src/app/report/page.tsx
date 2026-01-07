"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";

import logo from "@/assets/Logo.png";

interface Issue {
  [key: string]: string | number | boolean | null;
}

type DisplayField = {
  label: string;
  content: ReactNode;
};

const CHECKBOX_FIELDS = [
  { key: "Untitled checkboxes field (Bug/Software Malfunction)", label: "Bug / Software Malfunction" },
  { key: "Untitled checkboxes field (Data Inaccuracy)", label: "Data Inaccuracy" },
  { key: "Untitled checkboxes field (Performance Issue (Slow/Unresponsive))", label: "Performance Issue" },
  { key: "Untitled checkboxes field (User Interface/Experience Issue)", label: "UI / UX Issue" },
  { key: "Untitled checkboxes field (Security Vulnerability)", label: "Security Vulnerability" },
  { key: "Untitled checkboxes field (Feature Request/Suggestion)", label: "Feature Request" },
  { key: "Untitled checkboxes field (Other (Please describe in detail below))", label: "Other" },
];

const DETAIL_FIELDS = [
  { key: "Submission ID", label: "Submission ID" },
  { key: "Respondent ID", label: "Respondent ID" },
  { key: "Submitted at", label: "Submitted At" },
  { key: "What is the nature of the error you are reporting?", label: "Nature of Error" },
  { key: "Please describe the error in detail. What were you doing when the error occurred, and what was the unexpected behavior?", label: "Error Details" },
  { key: "What is the expected behavior when performing the actions that led to the error?", label: "Expected Behavior" },
  { key: "Have you found any workarounds for this error? If yes, please describe them.", label: "Workarounds" },
  { key: "If possible, please upload any relevant screenshots or error logs.", label: "Attachments" },
];

export default function ReportPage() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Issue | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch("/api/issues");
        const data = await res.json();
        const sorted = Array.isArray(data)
          ? [...data].sort(
              (a, b) => getIssueTimestamp(b) - getIssueTimestamp(a),
            )
          : [];
        setIssues(sorted);
      } catch (err) {
        console.error("Fetch error:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading)
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-slate-600 text-lg">Loading data...</p>
      </div>
    );

  return (
    <main className="min-h-screen bg-slate-100 pt-[120px] sm:pt-[90px] lg:pt-[80px]">
      {/* Top Bar */}
      <header className="absolute left-0 top-0 w-full bg-black text-white shadow-md">
        <div className="w-full px-4 py-4 sm:px-6 sm:py-4 lg:px-[35px]">
          <div className="mx-auto flex w-full max-w-[90rem] flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <Link
              href="/"
              className="flex items-center gap-3 text-white transition hover:text-slate-100"
            >
              <Image
                src={logo}
                alt="Shipnoise Logo"
                width={38}
                height={40}
                className="h-[40px] w-[38px] object-contain"
                priority
              />
              <span
                className="text-[22px] font-bold sm:text-[24px]"
                style={{ fontFamily: "Mukta, sans-serif" }}
              >
                Shipnoise
              </span>
            </Link>

            <div className="flex flex-col items-start gap-1 text-left text-white sm:items-end sm:text-right">
              <h1
                className="text-lg font-semibold tracking-wide sm:text-xl"
                style={{ fontFamily: "Montserrat, sans-serif" }}
              >
                Issue Report Dashboard
              </h1>
              <p className="text-sm opacity-80 sm:text-base">
                Total: {issues.length} submissions
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-md">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] divide-y divide-slate-200 text-xs sm:text-sm">
              <thead className="bg-slate-100 text-left font-semibold text-slate-700">
                <tr>
                  <th className="px-4 py-3 sm:px-6">Submission ID</th>
                  <th className="px-4 py-3 sm:px-6">Submitted At</th>
                  <th className="px-4 py-3 sm:px-6">Nature of Error</th>
                  <th className="px-4 py-3 text-center sm:px-6">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {issues.map((issue, i) => (
                  <tr
                    key={i}
                    className="cursor-pointer transition-colors hover:bg-slate-50"
                    onClick={() => setSelected(issue)}
                  >
                    <td className="px-4 py-3 sm:px-6">{toDisplayString(issue["Submission ID"] ?? issue.ID ?? i + 1)}</td>
                    <td className="px-4 py-3 sm:px-6">
                      {formatDateValue(
                        issue["Submitted at"] ?? issue.Timestamp ?? null,
                      )}
                    </td>
                    <td className="px-4 py-3 sm:px-6">
                      {toDisplayString(issue["What is the nature of the error you are reporting?"] ?? "(no title)")}
                    </td>
                    <td className="px-4 py-3 text-center sm:px-6">
                      <button
                        type="button"
                        className="rounded-full bg-slate-800 px-3 py-1 text-[11px] font-semibold text-white shadow-sm transition hover:bg-slate-700 sm:px-4 sm:py-1.5 sm:text-xs"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal */}
        {selected && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 py-6 backdrop-blur-sm sm:px-6">
            <div className="w-full max-h-[90vh] max-w-3xl overflow-y-auto rounded-2xl bg-white p-5 shadow-xl sm:p-6">
              <header className="flex flex-col gap-3 border-b pb-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 sm:text-xl">
                    Issue Details — {toDisplayString(selected["Submission ID"])}
                  </h3>
                  <p className="text-sm text-slate-500 sm:text-base">
                    Submitted:{" "}
                    {formatDateValue(
                      selected["Submitted at"] ?? selected.Timestamp ?? null,
                    )}
                  </p>
                </div>
                <button
                  onClick={() => setSelected(null)}
                  className="self-start rounded-full border border-slate-300 px-3 py-1.5 text-sm text-slate-700 transition hover:bg-slate-100 sm:self-auto"
                >
                  Close
                </button>
              </header>

              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                {buildDisplayFields(selected).map(({ label, content }) => (
                  <div key={label} className="rounded-xl border border-slate-100 bg-slate-50 p-4 text-sm">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
                    <div className="mt-1 space-y-2 break-words text-slate-800">{content}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

/* === Helper Functions === */
const DATE_FIELD_KEYS = [
  "Submitted at",
  "Submitted At",
  "Timestamp",
  "timestamp",
] as const;
const ATTACHMENT_FIELD_KEYS = new Set([
  "If possible, please upload any relevant screenshots or error logs.",
  "Attachments",
]);

function getIssueTimestamp(issue: Issue | null | undefined): number {
  if (!issue || typeof issue !== "object") return 0;
  for (const key of DATE_FIELD_KEYS) {
    const timestamp = parseTimestamp(issue[key]);
    if (timestamp !== null) return timestamp;
  }
  return 0;
}

function formatDateValue(raw: unknown): string {
  const timestamp = parseTimestamp(raw);
  if (timestamp === null) return "—";
  return formatUtcTimestamp(timestamp);
}

function parseTimestamp(raw: unknown): number | null {
  if (raw === null || raw === undefined) return null;

  if (typeof raw === "number") {
    if (!Number.isFinite(raw)) return null;
    return normalizeEpoch(raw);
  }

  if (typeof raw === "string") {
    const trimmed = raw.trim();
    if (!trimmed) return null;

    const direct = new Date(trimmed);
    if (!Number.isNaN(direct.getTime())) return direct.getTime();

    const asNumber = Number(trimmed);
    if (!Number.isNaN(asNumber)) return normalizeEpoch(asNumber);
  }

  return null;
}

function normalizeEpoch(value: number): number | null {
  if (!Number.isFinite(value)) return null;

  const asMillis = new Date(value);
  if (!Number.isNaN(asMillis.getTime()) && asMillis.getUTCFullYear() >= 2000) {
    return asMillis.getTime();
  }

  const asSeconds = new Date(value * 1000);
  if (!Number.isNaN(asSeconds.getTime())) {
    return asSeconds.getTime();
  }

  if (!Number.isNaN(asMillis.getTime())) {
    return asMillis.getTime();
  }

  return null;
}

function formatUtcTimestamp(epochMs: number): string {
  const date = new Date(epochMs);
  if (Number.isNaN(date.getTime())) return "—";

  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  const hours = String(date.getUTCHours()).padStart(2, "0");
  const minutes = String(date.getUTCMinutes()).padStart(2, "0");
  const seconds = String(date.getUTCSeconds()).padStart(2, "0");

  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds} UTC+0`;
}

function buildDisplayFields(issue: Issue): DisplayField[] {
  const entries: DisplayField[] = [];

  DETAIL_FIELDS.forEach(({ key, label }) => {
    const raw = issue[key];

    entries.push({ label, content: renderFieldValue(key, raw) });
  });

  const checkboxSelections = CHECKBOX_FIELDS.filter(({ key }) => isTruthy(issue[key])).map(({ label }) => label);
  entries.splice(4, 0, {
    label: "Error Categories",
    content: <span>{checkboxSelections.length ? checkboxSelections.join(", ") : "None selected"}</span>,
  });

  return entries;
}

function renderFieldValue(fieldKey: string, raw: unknown): ReactNode {
  if (DATE_FIELD_KEYS.map((key) => key.toLowerCase()).includes(fieldKey.toLowerCase())) {
    return <span>{formatDateValue(raw)}</span>;
  }

  if (ATTACHMENT_FIELD_KEYS.has(fieldKey)) {
    return renderAttachmentValue(raw);
  }

  return <span>{toDisplayString(raw)}</span>;
}

function renderAttachmentValue(raw: unknown): ReactNode {
  const urls = collectAttachmentUrls(raw);
  if (!urls.length) {
    return <span>{toDisplayString(raw)}</span>;
  }

  return urls.map((url, index) => (
    <div key={url ?? index} className="space-y-1">
      <a
        href={url}
        target="_blank"
        rel="noreferrer"
        className="text-slate-600 underline decoration-slate-300 underline-offset-4 transition hover:text-slate-800"
      >
        View attachment {urls.length > 1 ? index + 1 : ""}
      </a>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={url}
        alt={`Attachment ${index + 1}`}
        className="max-h-80 w-full rounded-lg border border-slate-200 object-contain"
        loading="lazy"
      />
    </div>
  ));
}

function collectAttachmentUrls(raw: unknown): string[] {
  if (!raw) return [];

  const fromArray =
    Array.isArray(raw) ?
      raw
        .map((item) => (typeof item === "string" ? item : toDisplayString(item)))
        .flatMap((item) => extractUrls(item))
    : extractUrls(typeof raw === "string" ? raw : toDisplayString(raw));

  return fromArray.filter(Boolean);
}

function extractUrls(text: string): string[] {
  const regex = /https?:\/\/[^\s)]+/g;
  const matches = text.match(regex);
  if (!matches) return [];

  return matches.map((url) => url.replace(/[.,)]+$/, ""));
}

function toDisplayString(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value.trim() || "—";
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value))
    return value.map((v) => toDisplayString(v)).filter((v) => v !== "—").join(", ") || "—";
  return JSON.stringify(value);
}

function isTruthy(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === "boolean") return value;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    return normalized === "true" || normalized === "yes" || normalized === "1";
  }
  if (typeof value === "number") return value !== 0;
  return false;
}
