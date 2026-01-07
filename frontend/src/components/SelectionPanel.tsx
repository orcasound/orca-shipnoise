'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import AvailableRecordings, { type RecordingEntry } from '@/components/AvailableRecordings';
import DeleteIcon from '@/assets/delete.svg';
import WarningIcon from '@/assets/Warning.svg';
import SearchIcon from '@/assets/Search.svg';

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
  }
}

type VesselOption = {
  name: string;
};

// Update 1: Matches the new API response structure
type ClipApiResult = {
  site: string;
  date_utc?: string;
  mmsi?: string | null;
  shipname?: string | null;
  audio_urls?: string[] | null;
  cpa_distance_m?: number | null;
  t_cpa?: string | null;
  center_segment_index?: number;
};

type WarningInfo = {
  icon: string;
  content: React.ReactNode;
};

const SITE_LABELS: Record<string, string> = {
  bush_point: 'Bush Point',
  orcasound_lab: 'Orcasound Lab',
  port_townsend: 'Port Townsend',
  sunset_bay: 'Sunset Bay',
};

const SITE_OPTIONS = Object.entries(SITE_LABELS).map(([value, label]) => ({
  value,
  label,
}));

const CLIPS_API_BASE_URL = process.env.NEXT_PUBLIC_CLIPS_API_BASE_URL?.replace(/\/$/, '');

const buildBackendUrl = (path: string, params: URLSearchParams): string | null => {
  if (!CLIPS_API_BASE_URL) return null;
  const url = new URL(path, `${CLIPS_API_BASE_URL}/`);
  for (const [key, value] of params.entries()) {
    url.searchParams.append(key, value);
  }
  return url.toString();
};

const SITE_VALUES = SITE_OPTIONS.map((option) => option.value);

const formatShipName = (value?: string | null): string | undefined => {
  if (!value) return undefined;
  const cleaned = value.replace(/[_\s]+/g, ' ').trim();
  if (!cleaned) return undefined;
  return cleaned
    .split(' ')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
    .join(' ');
};

const normalizeNameForSearch = (value: string): string =>
  value.replace(/[_\s]+/g, ' ').trim().toLowerCase();

const formatTitleCase = (value: string): string =>
  value
    .split(' ')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
    .join(' ');

interface VesselInputProps {
  options: VesselOption[];
  onChange: (option: VesselOption | null) => void;
  placeholder: string;
  value?: string;
  onInputChange?: (value: string) => void;
}

// AutoComplete input for Vessel
const VesselInput: React.FC<VesselInputProps> = ({ options, onChange, placeholder, value, onInputChange }) => {
  const [filteredOptions, setFilteredOptions] = useState<VesselOption[]>([]);
  const [showOptions, setShowOptions] = useState(false);
  const [suppressAutoOpen, setSuppressAutoOpen] = useState(true);
  const inputValue = value ?? '';
  const latestInputRef = useRef(inputValue);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    latestInputRef.current = inputValue;
  }, [inputValue]);

  const updateFilteredOptions = useCallback((val: string, optionList: VesselOption[]) => {
    const normalizedVal = normalizeNameForSearch(val);
    if (!normalizedVal.length) {
      setFilteredOptions([]);
      setShowOptions(false);
      return;
    }

    const filtered = optionList.filter((opt: VesselOption) =>
      normalizeNameForSearch(opt.name).includes(normalizedVal)
    );
    setFilteredOptions(filtered);
    setShowOptions(!suppressAutoOpen && filtered.length > 0);
  }, [suppressAutoOpen]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setSuppressAutoOpen(false);
    onInputChange?.(val);
    updateFilteredOptions(val, options);
  };

  useEffect(() => {
    updateFilteredOptions(latestInputRef.current, options);
  }, [options, updateFilteredOptions]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(event.target as Node)) {
        setShowOptions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleInputFocus = () => {
    if (!suppressAutoOpen && filteredOptions.length > 0) {
      setShowOptions(true);
    }
  };

  const handleSelect = (option: VesselOption) => {
    setSuppressAutoOpen(true);
    setShowOptions(false);
    setFilteredOptions([]);
    onChange(option);
    onInputChange?.(option.name);
  };
  const handleClear = () => {
    setSuppressAutoOpen(false);
    setFilteredOptions([]);
    setShowOptions(false);
    onChange(null);
    onInputChange?.('');
  };

  return (
    <div className="relative w-full" ref={containerRef}>
      <input
        type="text"
        value={inputValue}
        onChange={handleInputChange}
        onFocus={handleInputFocus}
        placeholder={placeholder}
        className="h-[42px] w-full rounded-[4px] border border-gray-300 bg-white px-4 text-left placeholder:text-left focus:border-[#111827] focus:outline-none sm:px-5"
      />
      {inputValue && (
        <button
          type="button"
          onClick={handleClear}
          className="absolute right-4 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center cursor-pointer sm:right-5"
        >
          <Image
            src={DeleteIcon}
            alt="Clear"
            width={20}
            height={20}
            className="h-full w-full object-contain"
          />
        </button>
      )}
      {showOptions && filteredOptions.length > 0 && (
        <div className="absolute top-full left-0 right-0 z-10 mt-2 max-h-48 overflow-y-auto rounded-[4px] border border-gray-300 bg-white text-left shadow-lg">
          {filteredOptions.map((opt, idx) => (
            <div
              key={idx}
              className="cursor-pointer p-2 text-left transition hover:bg-gray-100"
              onClick={() => handleSelect(opt)}
            >
              <div className="font-medium text-gray-800">{opt.name}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};


const SelectionPanel = () => {
  const [selectedVessel, setSelectedVessel] = useState<VesselOption | null>(null);
  const [showRecordings, setShowRecordings] = useState(false);
  const [vesselInputValue, setVesselInputValue] = useState('');
  const [warningInfo, setWarningInfo] = useState<WarningInfo | null>(null);
  const [hideDropdownSignal, setHideDropdownSignal] = useState(0);
  const [recordings, setRecordings] = useState<RecordingEntry[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [vesselOptions, setVesselOptions] = useState<VesselOption[]>([]);
  
  // Optimization: Ref to store the AbortController for the main search
  const mainSearchAbortController = useRef<AbortController | null>(null);

  useEffect(() => {
    const normalizedValue = normalizeNameForSearch(vesselInputValue);
    if (!normalizedValue) {
      setVesselOptions([]);
      return;
    }

    const controller = new AbortController();
    
    // Optimization: Debounce the suggestion fetch by 300ms
    // This prevents firing a request for every single keystroke
    const timeoutId = setTimeout(async () => {
      try {
        const params = new URLSearchParams({
          q: normalizedValue,
          limit: '20',
        });
        const url = buildBackendUrl('/vessels/search', params);
        if (!url) {
          console.error('NEXT_PUBLIC_CLIPS_API_BASE_URL is not configured');
          return;
        }
        const response = await fetch(url, {
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error(`Suggestion request failed with ${response.status}`);
        }
        const payload = await response.json();
        const names: string[] = Array.isArray(payload.results) ? payload.results : [];
        setVesselOptions(
          names.map((name) => ({
            name: formatShipName(name) ?? name,
          })),
        );
      } catch (error) {
        if ((error as Error).name === 'AbortError') return;
        console.error('Failed to fetch vessel suggestions', error);
      }
    }, 300); // 300ms delay

    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, [vesselInputValue]);

  const handleVesselInputChange = (value: string) => {
    setVesselInputValue(value);
    setWarningInfo(null);

    const normalizedValue = normalizeNameForSearch(value);
    const match = vesselOptions.find(
      (opt) => normalizeNameForSearch(opt.name) === normalizedValue
    );

    setSelectedVessel(match ?? null);
  };

  const handleVesselSelect = (option: VesselOption | null) => {
    setSelectedVessel(option);
    setVesselInputValue(option?.name ?? '');
    setWarningInfo(null);
  };

  const normalizedInput = vesselInputValue.trim();

  const normalizeClip = (clip: ClipApiResult): RecordingEntry => {
    const siteKey = clip.site?.replace(/\s+/g, '_').toLowerCase();
    const locationLabel =
      (siteKey && SITE_LABELS[siteKey]) ||
      (clip.site ? formatTitleCase(clip.site.replace(/[_\s]+/g, ' ')) : 'Unknown site');

    const audioSources = Array.isArray(clip.audio_urls)
      ? clip.audio_urls.filter((url) => typeof url === 'string' && url.trim().length > 0)
      : [];

    const vesselName =
      formatShipName(clip.shipname) ??
      formatShipName(clip.mmsi ?? '') ??
      clip.shipname ??
      clip.mmsi ??
      'Unknown vessel';
      
    return {
      vessel: vesselName,
      mmsi: clip.mmsi ?? undefined,
      location: locationLabel,
      date: clip.date_utc,
      time: undefined,
      timestamp: clip.t_cpa ?? null,
      audioUrls: audioSources, // Mapping to the new interface
      cpaDistanceMeters: clip.cpa_distance_m ?? undefined,
      noiseLevelDb: undefined,
    };
  };

  const handleSearchClick = async () => {
    // Optimization: Cancel any previous pending search requests
    if (mainSearchAbortController.current) {
      mainSearchAbortController.current.abort();
    }
    mainSearchAbortController.current = new AbortController();

    setIsSearching(true);
    setWarningInfo(null);

    try {
      const searchDateIso = new Date().toISOString().slice(0, 10);
      const requestEndDate = searchDateIso;
      const startDateObj = new Date(searchDateIso);
      startDateObj.setUTCDate(startDateObj.getUTCDate() - 59);
      const requestStartDate = startDateObj.toISOString().slice(0, 10);

      const params = new URLSearchParams({
        shipname: normalizedInput,
        start_date: requestStartDate,
        end_date: requestEndDate,
        limit_per_site: '5',
      });
      SITE_VALUES.forEach((site) => params.append('sites', site));
      const url = buildBackendUrl('/clips/search', params);
      if (!url) {
        throw new Error('NEXT_PUBLIC_CLIPS_API_BASE_URL is not configured');
      }
      
      const response = await fetch(url, {
        signal: mainSearchAbortController.current.signal
      });
      
      if (!response.ok) {
        throw new Error(`Clip search failed with ${response.status}`);
      }

      const payload = await response.json();
      const clips: ClipApiResult[] = Array.isArray(payload.results)
        ? payload.results
        : [];
      const responseStartDate: string | undefined =
        typeof payload.start_date === 'string' ? payload.start_date : undefined;
      const responseEndDate: string | undefined =
        typeof payload.end_date === 'string' ? payload.end_date : undefined;
      const dateRangeLabel: string | undefined =
        typeof payload.date_range_label === 'string'
          ? payload.date_range_label
          : responseStartDate && responseEndDate
            ? responseStartDate === responseEndDate
              ? responseStartDate
              : `${responseStartDate} – ${responseEndDate}`
            : undefined;

      const normalizedRecordings = clips.map(normalizeClip);

      if (normalizedRecordings.length === 0) {
        setShowRecordings(false);
        setWarningInfo({
          icon: WarningIcon,
          content: dateRangeLabel
            ? `No recordings match that vessel between ${dateRangeLabel}.`
            : 'No recordings found for that vessel.',
        });
        return;
      }

      const vesselLabel = (selectedVessel?.name ?? normalizedInput) || 'ALL';

      window.gtag?.('event', 'vessel_search', {
        event_category: 'selection_panel',
        event_label: vesselLabel,
        vessel: vesselLabel,
        site: 'ALL_SITES',
        date: searchDateIso,
        date_window: dateRangeLabel ?? 'LAST_60_DAYS',
        date_range_label: dateRangeLabel ?? 'LAST_60_DAYS',
      });

      setRecordings(normalizedRecordings);
      setShowRecordings(true);
      setHideDropdownSignal((prev) => prev + 1);
      setWarningInfo(null);
    } catch (error) {
      if ((error as Error).name === 'AbortError') return;
      console.error('Failed to load clips', error);
      const message =
        (error as Error).message?.includes('NEXT_PUBLIC_CLIPS_API_BASE_URL') === true
          ? 'Search unavailable: backend URL is not configured.'
          : 'Unable to load recordings right now. Please try again.';
      setShowRecordings(false);
      setWarningInfo({
        icon: WarningIcon,
        content: message,
      });
    } finally {
      // Only set searching to false if we weren't aborted
      if (mainSearchAbortController.current && !mainSearchAbortController.current.signal.aborted) {
         setIsSearching(false);
      }
    }
  };

  const iconSize = 15;

  return (
    <div className="w-full bg-white">
      <div className="w-full px-4 pb-[30px] pt-6 sm:px-6 md:pt-10">
        <div className="mx-auto flex w-full max-w-[90rem] flex-col gap-[30px]">
          {/* Search Inputs */}
          <div className="flex justify-center">
            <div className="w-full max-w-[90rem] rounded-[8px] border-2 border-gray-200 bg-white px-5 py-6 md:h-[220px] md:px-[25px] md:py-[25px]">
              <div className="mb-4 w-full md:mb-[15px] md:h-[56px]">
                <div
                  className="flex items-center gap-2 text-left"
                  style={{
                    color: '#111827',
                    fontSize: '22px',
                    fontWeight: 600,
                    lineHeight: '28px',
                    fontFamily: 'Montserrat, sans-serif',
                  }}
                >
                  <Image
                    src={SearchIcon}
                    alt="Search"
                    width={18}
                    height={18}
                    className="h-[18px] w-[18px] object-contain"
                  />
                  Explore Shipnoise Recordings
                </div>
                <p className="mt-1 text-left text-[#9CA3AF] text-[18px] leading-[28px] font-medium">
                  Enter a vessel name to discover and listen to its underwater sound recordings
                </p>
              </div>

              <div className="mt-5 w-full">
                <div className="flex w-full flex-col gap-4 md:flex-row md:flex-wrap md:items-end md:gap-[30px]">
                  <div className="flex w-full flex-col gap-2 md:flex-1">
                    <span
                      className="text-sm font-medium text-left text-[#374151] md:text-[14px]"
                      style={{ lineHeight: '20px' }}
                    >
                      Vessel Name
                    </span>
                    <VesselInput
                      key={hideDropdownSignal}
                      options={vesselOptions}
                      onChange={handleVesselSelect}
                      onInputChange={handleVesselInputChange}
                      value={vesselInputValue}
                      placeholder="Enter vessel name"
                    />
                  </div>

                  <div className="flex w-full flex-col justify-end md:w-[170px]">
                    <button
                      onClick={handleSearchClick}
                      className={`flex h-[42px] w-full items-center justify-center rounded-[100px] text-white transition ${
                        vesselInputValue.trim()
                          ? 'cursor-pointer bg-black hover:bg-black/90'
                          : 'cursor-default bg-[#C9C3C3]/40'
                      }`}
                      disabled={!vesselInputValue.trim()}
                    >
                      {isSearching ? 'Loading…' : 'Search'}
                    </button>
                  </div>
                </div>

                <div className="mt-2 min-h-[28px]">
                  <div className={`flex max-w-[1031px] items-center gap-2 ${warningInfo ? '' : 'invisible'}`}>
                    <span className="flex h-[15px] w-[15px] shrink-0">
                      {warningInfo && (
                        <Image
                          src={warningInfo.icon}
                          alt="Warning"
                          width={iconSize}
                          height={iconSize}
                          className="h-full w-full object-contain"
                        />
                      )}
                    </span>
                    <span
                      className="text-sm leading-5 text-[#716E6E]"
                      style={{ fontFamily: 'Montserrat, sans-serif' }}
                    >
                      {warningInfo?.content}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Recordings Table */}
          {showRecordings && (
            <AvailableRecordings
              recordings={recordings}
            />
          )}
        </div>
      </div>

    </div>
  );
};

export default SelectionPanel;
