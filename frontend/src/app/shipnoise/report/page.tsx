"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import {
  Box,
  Button,
  Container,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

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
      <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "#f8fafc",
        }}
      >
        <Typography sx={{ color: "#475569", fontSize: "18px" }}>
          Loading data...
        </Typography>
      </Box>
    );

  return (
    <Box
      component="main"
      sx={{
        minHeight: "100vh",
        bgcolor: "#f1f5f9",
        pt: { xs: "120px", sm: "90px", lg: "80px" },
      }}
    >
      {/* Top Bar */}
      <Box
        component="header"
        sx={{
          position: "absolute",
          left: 0,
          top: 0,
          width: "100%",
          bgcolor: "black",
          color: "white",
          boxShadow: "0 4px 6px rgba(0,0,0,0.15)",
        }}
      >
        <Box sx={{ width: "100%", px: { xs: 2, sm: 3, lg: "35px" }, py: { xs: 2, sm: 2 } }}>
          <Box
            sx={{
              mx: "auto",
              width: "100%",
              maxWidth: "90rem",
              display: "flex",
              flexDirection: { xs: "column", sm: "row" },
              gap: 2,
              alignItems: { sm: "center" },
              justifyContent: { sm: "space-between" },
            }}
          >
            <Box
              component={Link}
              href="/shipnoise"
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1.5,
                color: "white",
                textDecoration: "none",
                transition: "color 0.2s ease",
                "&:hover": { color: "#f1f5f9" },
              }}
            >
              <Image
                src={logo}
                alt="Shipnoise Logo"
                width={38}
                height={40}
                style={{ width: 38, height: 40, objectFit: "contain" }}
                priority
              />
              <Typography
                component="span"
                sx={{
                  fontSize: { xs: "22px", sm: "24px" },
                  fontWeight: 700,
                  fontFamily: "Mukta, sans-serif",
                }}
              >
                Shipnoise
              </Typography>
            </Box>

            <Stack
              spacing={0.5}
              alignItems={{ xs: "flex-start", sm: "flex-end" }}
              textAlign={{ xs: "left", sm: "right" }}
            >
              <Typography
                component="h1"
                sx={{
                  fontSize: { xs: "18px", sm: "20px" },
                  fontWeight: 600,
                  letterSpacing: "0.02em",
                  fontFamily: "Montserrat, sans-serif",
                }}
              >
                Issue Report Dashboard
              </Typography>
              <Typography sx={{ fontSize: { xs: "14px", sm: "16px" }, opacity: 0.8 }}>
                Total: {issues.length} submissions
              </Typography>
            </Stack>
          </Box>
        </Box>
      </Box>

      {/* Content */}
      <Container maxWidth="lg" sx={{ py: 5 }}>
        <Paper
          elevation={0}
          sx={{
            overflow: "hidden",
            borderRadius: "16px",
            border: "1px solid #e2e8f0",
            bgcolor: "white",
            boxShadow: "0 12px 24px rgba(15,23,42,0.08)",
          }}
        >
          <Box sx={{ overflowX: "auto" }}>
            <Table sx={{ minWidth: 720 }}>
              <TableHead>
                <TableRow sx={{ bgcolor: "#f1f5f9" }}>
                  <TableCell sx={{ px: { xs: 2, sm: 3 }, py: 1.5, fontWeight: 600, color: "#475569" }}>
                    Submission ID
                  </TableCell>
                  <TableCell sx={{ px: { xs: 2, sm: 3 }, py: 1.5, fontWeight: 600, color: "#475569" }}>
                    Submitted At
                  </TableCell>
                  <TableCell sx={{ px: { xs: 2, sm: 3 }, py: 1.5, fontWeight: 600, color: "#475569" }}>
                    Nature of Error
                  </TableCell>
                  <TableCell
                    align="center"
                    sx={{ px: { xs: 2, sm: 3 }, py: 1.5, fontWeight: 600, color: "#475569" }}
                  >
                    Action
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {issues.map((issue, i) => (
                  <TableRow
                    key={i}
                    hover
                    onClick={() => setSelected(issue)}
                    sx={{ cursor: "pointer" }}
                  >
                    <TableCell sx={{ px: { xs: 2, sm: 3 }, py: 1.5 }}>
                      {toDisplayString(issue["Submission ID"] ?? issue.ID ?? i + 1)}
                    </TableCell>
                    <TableCell sx={{ px: { xs: 2, sm: 3 }, py: 1.5 }}>
                      {formatDateValue(issue["Submitted at"] ?? issue.Timestamp ?? null)}
                    </TableCell>
                    <TableCell sx={{ px: { xs: 2, sm: 3 }, py: 1.5 }}>
                      {toDisplayString(
                        issue["What is the nature of the error you are reporting?"] ?? "(no title)"
                      )}
                    </TableCell>
                    <TableCell align="center" sx={{ px: { xs: 2, sm: 3 }, py: 1.5 }}>
                      <Button
                        variant="contained"
                        sx={{
                          borderRadius: "999px",
                          bgcolor: "#1f2937",
                          fontSize: { xs: "11px", sm: "12px" },
                          fontWeight: 600,
                          textTransform: "none",
                          px: { xs: 2, sm: 3 },
                          py: { xs: 0.5, sm: 0.75 },
                          minHeight: "auto",
                          "&:hover": { bgcolor: "#334155" },
                        }}
                      >
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </Paper>

        {/* Modal */}
        {selected && (
          <Box
            sx={{
              position: "fixed",
              inset: 0,
              zIndex: 50,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: "rgba(0,0,0,0.4)",
              px: { xs: 2, sm: 3 },
              py: 3,
              backdropFilter: "blur(6px)",
            }}
          >
            <Paper
              sx={{
                width: "100%",
                maxWidth: "48rem",
                maxHeight: "90vh",
                overflowY: "auto",
                borderRadius: "16px",
                p: { xs: 2, sm: 3 },
                boxShadow: "0 24px 48px rgba(15,23,42,0.25)",
              }}
            >
              <Box
                component="header"
                sx={{
                  display: "flex",
                  flexDirection: { xs: "column", sm: "row" },
                  gap: 2,
                  alignItems: { sm: "center" },
                  justifyContent: { sm: "space-between" },
                  borderBottom: "1px solid #e2e8f0",
                  pb: 1.5,
                }}
              >
                <Box>
                  <Typography sx={{ fontSize: { xs: "18px", sm: "20px" }, fontWeight: 600, color: "#0f172a" }}>
                    Issue Details — {toDisplayString(selected["Submission ID"])}
                  </Typography>
                  <Typography sx={{ fontSize: { xs: "14px", sm: "16px" }, color: "#64748b" }}>
                    Submitted: {formatDateValue(selected["Submitted at"] ?? selected.Timestamp ?? null)}
                  </Typography>
                </Box>
                <Button
                  onClick={() => setSelected(null)}
                  variant="outlined"
                  sx={{
                    alignSelf: { xs: "flex-start", sm: "auto" },
                    borderRadius: "999px",
                    borderColor: "#cbd5f5",
                    color: "#334155",
                    textTransform: "none",
                    "&:hover": { bgcolor: "#f1f5f9", borderColor: "#cbd5f5" },
                  }}
                >
                  Close
                </Button>
              </Box>

              <Box
                sx={{
                  mt: 2.5,
                  display: "grid",
                  gap: 2,
                  gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                }}
              >
                {buildDisplayFields(selected).map(({ label, content }) => (
                  <Paper
                    key={label}
                    variant="outlined"
                    sx={{
                      borderRadius: "12px",
                      borderColor: "#f1f5f9",
                      bgcolor: "#f8fafc",
                      p: 2,
                      fontSize: "14px",
                    }}
                  >
                    <Typography
                      sx={{
                        fontSize: "11px",
                        fontWeight: 600,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        color: "#94a3b8",
                      }}
                    >
                      {label}
                    </Typography>
                    <Box sx={{ mt: 0.5, color: "#1e293b", wordBreak: "break-word" }}>
                      {content}
                    </Box>
                  </Paper>
                ))}
              </Box>
            </Paper>
          </Box>
        )}
      </Container>
    </Box>
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
    <Box key={url ?? index} sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
      <Box
        component="a"
        href={url}
        target="_blank"
        rel="noreferrer"
        sx={{
          color: "#475569",
          textDecoration: "underline",
          textDecorationColor: "#cbd5e1",
          textUnderlineOffset: "4px",
          transition: "color 0.2s ease",
          "&:hover": { color: "#1e293b" },
        }}
      >
        View attachment {urls.length > 1 ? index + 1 : ""}
      </Box>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <Box
        component="img"
        src={url}
        alt={`Attachment ${index + 1}`}
        loading="lazy"
        sx={{
          maxHeight: 320,
          width: "100%",
          borderRadius: "8px",
          border: "1px solid #e2e8f0",
          objectFit: "contain",
        }}
      />
    </Box>
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
