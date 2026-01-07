'use client';

import React, { useEffect, useMemo, useState } from "react";
import Image from "next/image";
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
    <div className="mt-6 w-full">
      <div className="mx-auto w-full max-w-[90rem] px-4 md:px-0">
        {/* Header Bar */}
        <div className="flex w-full flex-wrap items-center bg-[#2D3147] px-4 py-6 md:h-[64px] md:flex-nowrap md:px-[25px]">
          <Image
            src={VesselIcon}
            alt="Vessel"
            width={23}
            height={28}
            className="mr-2 w-5 h-6"
            priority
          />
          <h3 className="text-lg font-semibold text-white md:text-xl">
            Explore Recordings of Vessel
            {vesselIdDisplay && (
              <>
                {` ${vesselIdDisplay}`}
                {recordingsLabel && (
                  <span
                    style={{
                      fontSize: '22px',
                      fontWeight: 300,
                      lineHeight: '28px',
                      fontFamily: 'Montserrat, sans-serif',
                    }}
                  >
                    {' '}
                    {recordingsLabel}
                  </span>
                )}
              </>
            )}
          </h3>
        </div>

        {/* Location Lists */}
        <div className="space-y-4">
          {groupedLocations.map(({ label, recordings: groupedRecordings }) => {
            const isExpanded = expandedLocations.has(label);
            const hasRecordings = groupedRecordings.length > 0;
            const countLabel = groupedRecordings.length;

            // Skip rendering locations with 0 recordings entirely if desired, 
            // but your design seems to keep them visible (via preferred list).
            // If preferred list items have 0 recordings, we might want to hide them?
            // Currently keeping logic to show headers even if empty for preferred locations.

            return (
              <div key={label} className="w-full overflow-hidden bg-[#E5E7EB]">
                {/* Accordion Header */}
                <div className="flex flex-col gap-2 px-4 py-3 md:h-[46px] md:flex-row md:items-center md:justify-between md:px-[25px]">
                  <div className="text-left text-[14px] font-normal text-gray-800">
                    <button
                      className="cursor-pointer hover:underline"
                      style={{
                        color: '#111827',
                        fontSize: '22px',
                        fontWeight: 600,
                        lineHeight: '28px',
                        fontFamily: 'Montserrat, sans-serif',
                      }}
                      onClick={() => openHydrophoneLocation(label)}
                    >
                      {label}
                    </button>{' '}
                    <span
                      style={{
                        fontSize: '22px',
                        fontWeight: 300,
                        lineHeight: '28px',
                        fontFamily: 'Montserrat, sans-serif',
                      }}
                    >
                      ({countLabel} recording{countLabel === 1 ? '' : 's'})
                    </span>
                  </div>
                  <div className="flex items-center justify-end">
                    {hasRecordings ? (
                      <button
                        type="button"
                        onClick={() => handleToggleLocation(label, hasRecordings)}
                        className={`flex h-5 w-5 items-center justify-center transform transition-transform ${
                          hasRecordings ? 'cursor-pointer' : 'cursor-default opacity-40'
                        } ${isExpanded ? 'rotate-0' : 'rotate-180'}`}
                        aria-expanded={isExpanded}
                        aria-label={isExpanded ? `Collapse ${label}` : `Expand ${label}`}
                      >
                        <Image
                          src={UpIcon}
                          alt=""
                          width={20}
                          height={20}
                          className="h-full w-full"
                        />
                      </button>
                    ) : (
                      <div className="h-5 w-5" aria-hidden />
                    )}
                  </div>
                </div>

                {/* Accordion Content */}
                {isExpanded && hasRecordings && (
                  <div className="bg-white">
                    {groupedRecordings.map((rec, idx) => {
                      // KEY OPTIMIZATION: Use ID if available, fallback to URL+Index
                      const uniqueKey = rec.id ?? `${rec.audioUrls?.[0] ?? 'missing'}-${idx}`;
                      
                      return (
                        <div
                          key={uniqueKey}
                          className="w-full border-b border-black px-4 py-5 md:px-[45px] md:py-[25px]"
                        >
                          <InlineWavePlayer
                            audioUrls={rec.audioUrls}
                            date={rec.date}
                            time={rec.time}
                            timestamp={rec.timestamp}
                          />
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default AvailableRecordings;