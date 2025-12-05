'use client';

import React, { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import VesselIcon from "@/assets/VesselIcon.png";
import UpIcon from "@/assets/up.svg";
import InlineWavePlayer from "@/components/InlineWavePlayer";

export type RecordingEntry = {
  vessel?: string | null;
  mmsi?: string | null;
  location: string;
  date?: string;
  time?: string;
  timestamp?: string | null;
  recordUrl: string;
  cpaDistanceMeters?: number | null;
  noiseLevelDb?: number | null;
};

interface AvailableRecordingsProps {
  recordings: RecordingEntry[];
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

const AvailableRecordings: React.FC<AvailableRecordingsProps> = ({ recordings }) => {
  const [expandedLocations, setExpandedLocations] = useState<Set<string>>(new Set());
  const openHydrophoneLocation = (label: string) => {
    const acceptedLabel = label.toLowerCase().replace(/\s+/g, '-').replace(/[^\w-]/g, '');
    const url = `https://live.orcasound.net/listen/${acceptedLabel}`;
    window.open(url, "_blank");
  };

  useEffect(() => {
    document.querySelectorAll('script[src*="chimpstatic"]').forEach((s) => s.remove());

    const script = document.createElement("script");
    script.id = "mcjs";
    script.src = MAILCHIMP_SCRIPT + "?v=" + new Date().getTime();
    script.async = true;
    document.body.appendChild(script);
  }, []);

  const groupedLocations = useMemo(() => {
    const grouped: Record<string, RecordingEntry[]> = {};
    recordings.forEach((record) => {
      grouped[record.location] = grouped[record.location] || [];
      grouped[record.location].push(record);
    });

    const recordTimestamp = (record: RecordingEntry) => {
      if (record.date && record.time) {
        const combined = new Date(`${record.date} ${record.time}`);
        if (!Number.isNaN(combined.getTime())) {
          return combined.getTime();
        }
      }
      if (record.date) {
        const dateOnly = new Date(record.date);
        if (!Number.isNaN(dateOnly.getTime())) {
          return dateOnly.getTime();
        }
      }
      return 0;
    };

    const sortRecordingsDesc = (items: RecordingEntry[]) =>
      [...items].sort((a, b) => recordTimestamp(b) - recordTimestamp(a));

    const preferred = PREFERRED_LOCATIONS.map((label) => ({
      label,
      recordings: sortRecordingsDesc(grouped[label] ?? []),
    }));

    const others = Object.keys(grouped)
      .filter((label) => !PREFERRED_LOCATIONS.includes(label))
      .map((label) => ({ label, recordings: sortRecordingsDesc(grouped[label]) }));

    const sortedCombined = [...preferred, ...others].sort(
      (a, b) => b.recordings.length - a.recordings.length
    );

    return sortedCombined;
  }, [recordings]);

  const totalRecordings = recordings.length;
  const vesselIdDisplay = totalRecordings > 0 ? recordings[0].vessel : null;
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

  return (
    <div className="mt-6 w-full">
      <div className="mx-auto w-full max-w-[90rem] px-4 md:px-0">
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

        <div className="space-y-4">
          {groupedLocations.map(({ label, recordings: groupedRecordings }) => {
            const isExpanded = expandedLocations.has(label);
            const hasRecordings = groupedRecordings.length > 0;
            const countLabel = groupedRecordings.length;

            return (
              <div key={label} className="w-full overflow-hidden bg-[#E5E7EB]">
                <div className="flex flex-col gap-2 px-4 py-3 md:h-[46px] md:flex-row md:items-center md:justify-between md:px-[25px]">
                  <div className="text-left text-[14px] font-normal text-gray-800">
                    <button
                      className="cursor-pointer"
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
                      >
                        <Image
                          src={UpIcon}
                          alt={isExpanded ? 'Collapse section' : 'Expand section'}
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

                {isExpanded && hasRecordings && (
                  <div className="bg-white">
                    {groupedRecordings.map((rec, idx) => (
                      <div
                        key={`${rec.recordUrl}-${idx}`}
                        className="w-full border-b border-black px-4 py-5 md:px-[45px] md:py-[25px]"
                      >
                        <InlineWavePlayer
                          src={rec.recordUrl}
                          date={rec.date}
                          time={rec.time}
                          timestamp={rec.timestamp}
                        />
                      </div>
                    ))}
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
