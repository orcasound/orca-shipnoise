'use client';

import React, { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import {
  Box,
  IconButton,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import VesselIcon from "@/assets/VesselIcon.png";
import UpIcon from "@/assets/up.svg";
import InlineWavePlayer from "@/components/InlineWavePlayer";

// 1. Updated Interface: Added 'id' for better React keys
export type RecordingEntry = {
  id?: string; // <-- New field recommended for stable keys
  vessel?: string | null;
  mmsi?: string | null;
  location: string;
  date?: string;
  time?: string;
  timestamp?: string | null;
  audioUrls: string[]; 
  cpaDistanceMeters?: number | null;
  noiseLevelDb?: number | null;
};

interface AvailableRecordingsProps {
  recordings?: RecordingEntry[];
}

declare global {
  interface Window {
    mcpopup?: { open: () => void };
    mc4wp?: { forms: { show: () => void } };
  }
}

const MAILCHIMP_SCRIPT =
  "https://chimpstatic.com/mcjs-connected/js/users/30e5b89b891e7b961c63e7d39/2318c630b0adc777855362be3.js";

const PREFERRED_LOCATIONS = [
  "Sunset Bay",
  "Bush Point",
  "Port Townsend",
  "Orcasound Lab",
];

const AvailableRecordings: React.FC<AvailableRecordingsProps> = ({ recordings = [] }) => {
  // Optimization: Filter invalid recordings once
  const safeRecordings = useMemo(() => {
    return recordings
      .filter((record) =>
        Array.isArray(record.audioUrls) &&
        record.audioUrls.some((url) => typeof url === "string" && url.trim().length > 0)
      )
      .map((record) => ({
        ...record,
        location: record.location || "Unknown location",
      }));
  }, [recordings]);

  const [expandedLocations, setExpandedLocations] = useState<Set<string>>(new Set());

  const openHydrophoneLocation = (label: string) => {
    const normalizedLabel = label?.trim();
    if (!normalizedLabel) return;
    // Ensure slug is clean: "Orcasound Lab" -> "orcasound-lab"
    const acceptedLabel = normalizedLabel
      .toLowerCase()
      .replace(/\s+/g, "-")
      .replace(/[^\w-]/g, "");
    const url = `https://live.orcasound.net/listen/${acceptedLabel}`;
    window.open(url, "_blank");
  };

  useEffect(() => {
    // Mailchimp script injection (Legacy logic preserved)
    const existingScripts = document.querySelectorAll('script[src*="chimpstatic"]');
    existingScripts.forEach((s) => s.remove());

    const script = document.createElement("script");
    script.id = "mcjs";
    script.src = MAILCHIMP_SCRIPT + "?v=" + new Date().getTime();
    script.async = true;
    document.body.appendChild(script);
  }, []);

  const groupedLocations = useMemo(() => {
    const grouped: Record<string, RecordingEntry[]> = {};
    
    // Grouping
    safeRecordings.forEach((record) => {
      if (!grouped[record.location]) {
        grouped[record.location] = [];
      }
      grouped[record.location].push(record);
    });

    // Helper to parse sorting timestamp
    const getTimestamp = (record: RecordingEntry) => {
      // Try high-precision timestamp first (if your DB provides t_cpa in ISO)
      if (record.timestamp) {
        const ts = new Date(record.timestamp).getTime();
        if (!isNaN(ts)) return ts;
      }
      // Fallback to date + time fields
      if (record.date) {
        const dateTimeStr = record.time ? `${record.date} ${record.time}` : record.date;
        const ts = new Date(dateTimeStr).getTime();
        if (!isNaN(ts)) return ts;
      }
      return 0;
    };

    const sortDesc = (items: RecordingEntry[]) =>
      [...items].sort((a, b) => getTimestamp(b) - getTimestamp(a));

    // Split into Preferred vs Others
    const preferred = PREFERRED_LOCATIONS.map((label) => ({
      label,
      recordings: sortDesc(grouped[label] ?? []),
    }));

    const others = Object.keys(grouped)
      .filter((label) => !PREFERRED_LOCATIONS.includes(label))
      .map((label) => ({ label, recordings: sortDesc(grouped[label]) }));

    // Sort locations by number of recordings (descending)
    const sortedCombined = [...preferred, ...others].sort(
      (a, b) => b.recordings.length - a.recordings.length
    );

    return sortedCombined;
  }, [safeRecordings]);

  const totalRecordings = safeRecordings.length;
  const vesselIdDisplay = totalRecordings > 0 ? safeRecordings[0].vessel : null;
  const recordingsLabel = totalRecordings
    ? `(${totalRecordings} recording${totalRecordings === 1 ? '' : 's'})`
    : '';

  const handleToggleLocation = (location: string, hasRecordings: boolean) => {
    if (!hasRecordings) return;
    setExpandedLocations((prev) => {
      const next = new Set(prev);
      if (next.has(location)) {
        next.delete(location);
      } else {
        next.add(location);
      }
      return next;
    });
  };

  if (totalRecordings === 0) {
    return null; // Don't render empty container if filtered to 0
  }

  return (
    <Box sx={{ mt: 3, width: "100%" }}>
      <Box sx={{ mx: "auto", width: "100%", maxWidth: "90rem", px: { xs: 2, md: 0 } }}>
        {/* Header Bar */}
        <Box
          sx={{
            display: "flex",
            flexWrap: { xs: "wrap", md: "nowrap" },
            alignItems: "center",
            bgcolor: "#2D3147",
            px: { xs: 2, md: "25px" },
            py: 3,
            height: { md: 64 },
          }}
        >
          <Box sx={{ mr: 1, width: 20, height: 24, display: "flex", alignItems: "center" }}>
            <Image
              src={VesselIcon}
              alt="Vessel"
              width={23}
              height={28}
              style={{ width: "100%", height: "100%" }}
              priority
            />
          </Box>
          <Typography variant="h6" sx={{ color: "white", fontWeight: 600, fontSize: { xs: 18, md: 20 } }}>
            Explore Recordings of Vessel
            {vesselIdDisplay && (
              <>
                {` ${vesselIdDisplay}`}
                {recordingsLabel && (
                  <Box
                    component="span"
                    sx={{
                      fontSize: "22px",
                      fontWeight: 300,
                      lineHeight: "28px",
                      fontFamily: "Montserrat, sans-serif",
                    }}
                  >
                    {" "}
                    {recordingsLabel}
                  </Box>
                )}
              </>
            )}
          </Typography>
        </Box>

        {/* Location Lists */}
        <Stack spacing={2}>
          {groupedLocations.map(({ label, recordings: groupedRecordings }) => {
            const isExpanded = expandedLocations.has(label);
            const hasRecordings = groupedRecordings.length > 0;
            const countLabel = groupedRecordings.length;

            return (
              <Paper
                key={label}
                square
                elevation={0}
                sx={{ width: "100%", overflow: "hidden", bgcolor: "#E5E7EB", boxShadow: "none" }}
              >
                {/* Accordion Header */}
                <Stack
                  direction={{ xs: "column", md: "row" }}
                  spacing={{ xs: 1, md: 2 }}
                  alignItems={{ md: "center" }}
                  justifyContent={{ md: "space-between" }}
                  sx={{ px: { xs: 2, md: "25px" }, py: 1.5, height: { md: 46 } }}
                >
                  <Typography sx={{ textAlign: "left", color: "#111827", fontSize: "22px", fontWeight: 600, lineHeight: "28px", fontFamily: "Montserrat, sans-serif" }}>
                    <Box
                      component="button"
                      onClick={() => openHydrophoneLocation(label)}
                      sx={{
                        cursor: "pointer",
                        border: "none",
                        background: "transparent",
                        padding: 0,
                        color: "inherit",
                        font: "inherit",
                        textDecoration: "none",
                        "&:hover": { textDecoration: "underline" },
                      }}
                    >
                      {label}
                    </Box>{" "}
                    <Box
                      component="span"
                      sx={{
                        fontSize: "22px",
                        fontWeight: 300,
                        lineHeight: "28px",
                        fontFamily: "Montserrat, sans-serif",
                      }}
                    >
                      ({countLabel} recording{countLabel === 1 ? "" : "s"})
                    </Box>
                  </Typography>
                  <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
                    {hasRecordings ? (
                      <IconButton
                        onClick={() => handleToggleLocation(label, hasRecordings)}
                        aria-expanded={isExpanded}
                        aria-label={isExpanded ? `Collapse ${label}` : `Expand ${label}`}
                        sx={{
                          width: 24,
                          height: 24,
                          p: 0,
                          transform: isExpanded ? "rotate(0deg)" : "rotate(180deg)",
                          transition: "transform 0.2s ease",
                        }}
                      >
                        <Image src={UpIcon} alt="" width={20} height={20} style={{ width: "100%", height: "100%" }} />
                      </IconButton>
                    ) : (
                      <Box sx={{ width: 20, height: 20 }} aria-hidden />
                    )}
                  </Box>
                </Stack>

                {/* Accordion Content */}
                {isExpanded && hasRecordings && (
                  <Box sx={{ bgcolor: "white" }}>
                    {groupedRecordings.map((rec, idx) => {
                      const uniqueKey = rec.id ?? `${rec.audioUrls?.[0] ?? "missing"}-${idx}`;

                      return (
                        <Box
                          key={uniqueKey}
                          sx={{
                            width: "100%",
                            borderBottom: "1px solid black",
                            px: { xs: 2, md: "45px" },
                            py: { xs: 2.5, md: "25px" },
                          }}
                        >
                          <InlineWavePlayer
                            audioUrls={rec.audioUrls}
                            date={rec.date}
                            time={rec.time}
                            timestamp={rec.timestamp}
                          />
                        </Box>
                      );
                    })}
                  </Box>
                )}
              </Paper>
            );
          })}
        </Stack>
      </Box>
    </Box>
  );
};

export default AvailableRecordings;
