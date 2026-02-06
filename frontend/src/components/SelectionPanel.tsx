'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import {
  Box,
  Button,
  IconButton,
  InputAdornment,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
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
    <Box ref={containerRef} sx={{ position: 'relative', width: '100%' }}>
      <TextField
        fullWidth
        value={inputValue}
        onChange={handleInputChange}
        onFocus={handleInputFocus}
        placeholder={placeholder}
        variant="outlined"
        size="small"
        InputProps={{
          endAdornment: inputValue ? (
            <InputAdornment position="end">
              <IconButton
                size="small"
                onClick={handleClear}
                aria-label="Clear"
                sx={{ p: 0.25 }}
              >
                <Image
                  src={DeleteIcon}
                  alt="Clear"
                  width={20}
                  height={20}
                  style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                />
              </IconButton>
            </InputAdornment>
          ) : null,
        }}
        sx={{
          '& .MuiOutlinedInput-root': {
            height: 42,
            borderRadius: '4px',
            backgroundColor: 'white',
            '& fieldset': { borderColor: '#d1d5db' },
            '&:hover fieldset': { borderColor: '#111827' },
            '&.Mui-focused fieldset': { borderColor: '#111827' },
          },
          '& .MuiOutlinedInput-input': {
            px: { xs: 2, sm: 2.5 },
            py: 1,
          },
        }}
      />
      {showOptions && filteredOptions.length > 0 && (
        <Paper
          elevation={6}
          sx={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            zIndex: 10,
            mt: 1,
            maxHeight: 192,
            overflowY: 'auto',
            borderRadius: '4px',
            border: '1px solid #d1d5db',
          }}
        >
          <List dense disablePadding>
            {filteredOptions.map((opt, idx) => (
              <ListItemButton key={idx} onClick={() => handleSelect(opt)}>
                <ListItemText
                  primary={opt.name}
                  primaryTypographyProps={{ fontWeight: 500, color: '#1f2937' }}
                />
              </ListItemButton>
            ))}
          </List>
        </Paper>
      )}
    </Box>
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
    <Box sx={{ width: '100%', bgcolor: 'white' }}>
      <Box sx={{ width: '100%', px: { xs: 2, sm: 3 }, pb: '30px', pt: { xs: 3, md: 5 } }}>
        <Stack sx={{ mx: 'auto', width: '100%', maxWidth: '90rem' }} spacing={3.75}>
          {/* Search Inputs */}
          <Box sx={{ display: 'flex', justifyContent: 'center' }}>
            <Paper
              variant="outlined"
              sx={{
                width: '100%',
                maxWidth: '90rem',
                borderRadius: '8px',
                borderWidth: 2,
                borderColor: '#e5e7eb',
                px: { xs: 2.5, md: '25px' },
                py: { xs: 3, md: '25px' },
                height: { md: 220 },
              }}
            >
              <Box sx={{ mb: { xs: 2, md: '15px' }, height: { md: 56 } }}>
                <Stack direction="row" alignItems="center" spacing={1}>
                  <Image
                    src={SearchIcon}
                    alt="Search"
                    width={18}
                    height={18}
                    style={{ width: 18, height: 18, objectFit: 'contain' }}
                  />
                  <Typography
                    sx={{
                      color: '#111827',
                      fontSize: '22px',
                      fontWeight: 600,
                      lineHeight: '28px',
                      fontFamily: 'Montserrat, sans-serif',
                    }}
                  >
                    Explore Shipnoise Recordings
                  </Typography>
                </Stack>
                <Typography
                  sx={{
                    mt: 1,
                    color: '#9CA3AF',
                    fontSize: '18px',
                    lineHeight: '28px',
                    fontWeight: 500,
                  }}
                >
                  Enter a vessel name to discover and listen to its underwater sound recordings
                </Typography>
              </Box>

              <Box sx={{ mt: 2.5, width: '100%' }}>
                <Stack
                  direction={{ xs: 'column', md: 'row' }}
                  spacing={{ xs: 2, md: '30px' }}
                  alignItems={{ xs: 'stretch', md: 'flex-end' }}
                  flexWrap={{ md: 'wrap' }}
                >
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, flex: 1 }}>
                    <Typography
                      sx={{
                        fontSize: { xs: '14px', md: '14px' },
                        fontWeight: 500,
                        color: '#374151',
                        lineHeight: '20px',
                      }}
                    >
                      Vessel Name
                    </Typography>
                    <VesselInput
                      key={hideDropdownSignal}
                      options={vesselOptions}
                      onChange={handleVesselSelect}
                      onInputChange={handleVesselInputChange}
                      value={vesselInputValue}
                      placeholder="Enter vessel name"
                    />
                  </Box>

                  <Box sx={{ width: { xs: '100%', md: 170 }, display: 'flex', flexDirection: 'column' }}>
                    <Button
                      onClick={handleSearchClick}
                      disabled={!vesselInputValue.trim()}
                      variant="contained"
                      sx={{
                        height: 42,
                        width: '100%',
                        borderRadius: '100px',
                        textTransform: 'none',
                        color: 'white',
                        bgcolor: vesselInputValue.trim() ? 'black' : 'rgba(201,195,195,0.4)',
                        '&:hover': {
                          bgcolor: vesselInputValue.trim() ? 'rgba(0,0,0,0.9)' : 'rgba(201,195,195,0.4)',
                        },
                      }}
                    >
                      {isSearching ? 'Loading…' : 'Search'}
                    </Button>
                  </Box>
                </Stack>

                <Box sx={{ mt: 1, minHeight: 28 }}>
                  <Stack
                    direction="row"
                    spacing={1}
                    alignItems="center"
                    sx={{
                      maxWidth: 1031,
                      visibility: warningInfo ? 'visible' : 'hidden',
                    }}
                  >
                    <Box sx={{ display: 'flex', width: 15, height: 15, flexShrink: 0 }}>
                      {warningInfo && (
                        <Image
                          src={warningInfo.icon}
                          alt="Warning"
                          width={iconSize}
                          height={iconSize}
                          style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                        />
                      )}
                    </Box>
                    <Typography
                      sx={{
                        fontSize: '14px',
                        lineHeight: '20px',
                        color: '#716E6E',
                        fontFamily: 'Montserrat, sans-serif',
                      }}
                    >
                      {warningInfo?.content}
                    </Typography>
                  </Stack>
                </Box>
              </Box>
            </Paper>
          </Box>

          {/* Recordings Table */}
          {showRecordings && <AvailableRecordings recordings={recordings} />}
        </Stack>
      </Box>
    </Box>
  );
};

export default SelectionPanel;
