"""
Centralized site configuration for the shipnoise pipeline.

Adding or removing a site only requires a change here.
"""

S3_BUCKET            = "audio-orcasound-net"
KEEP_DAYS            = 5   # days of raw data to retain on disk
STALE_THRESHOLD_DAYS = 7   # days before a hydrophone is considered stale
ORCASITE_GRAPHQL = "https://live.orcasound.net/graphql"
AISSTREAM_WS     = "wss://stream.aisstream.io/v0/stream"

# AIS transit detection thresholds
RADIUS_M               = 30000  # search radius around each hydrophone
CPA_MAX_M              = 20000  # max closest-point-of-approach distance
MIN_SOG_KT             = 2      # min speed over ground (knots)
MIN_POINTS             = 3      # min AIS points to form a transit
MIN_DWELL_SEC          = 60     # min time vessel spends in radius
HIGH_QUALITY_THRESHOLD = 1000   # CPA distance for "high quality" tag

# Acoustic relevance CPA thresholds (merge_and_dedup)
DEFAULT_CPA_MAX_M    = 5000   # normal ships
LARGE_SHIP_CPA_MAX_M = 8000   # large vessels (> LARGE_SHIP_MIN_M)
SMALL_SHIP_CPA_MAX_M = 3000   # small / unknown ships (< SMALL_SHIP_MAX_M)
LARGE_SHIP_MIN_M     = 150    # length threshold for "large" classification
SMALL_SHIP_MAX_M     = 50     # length threshold for "small" classification

SITES = [
    {
        "slug":                   "bush-point",           # kebab-case (aisstream, collect)
        "key":                    "bush_point",            # underscore (processing, dirs)
        "s3_prefix":              "rpi_bush_point",        # S3 bucket prefix
        "hls_prefix":             "rpi_bush_point/hls/",   # S3 HLS prefix
        "cpa_overrides":          None,                    # use global defaults
        "confidence_thresholds":  None,                    # use global defaults
    },
    {
        "slug":                   "orcasound-lab",
        "key":                    "orcasound_lab",
        "s3_prefix":              "rpi_orcasound_lab",
        "hls_prefix":             "rpi_orcasound_lab/hls/",
        "cpa_overrides":          None,
        "confidence_thresholds":  None,
    },
    {
        "slug":                   "port-townsend",
        "key":                    "port_townsend",
        "s3_prefix":              "rpi_port_townsend",
        "hls_prefix":             "rpi_port_townsend/hls/",
        "cpa_overrides":          None,
        "confidence_thresholds":  None,
    },
    {
        "slug":       "sunset-bay",
        "key":        "sunset_bay",
        "s3_prefix":  "rpi_sunset_bay",
        "hls_prefix": "rpi_sunset_bay/hls/",
        # Sunset Bay ships are routinely detected 6-8 km out, so widen the gates
        "cpa_overrides": {"default": 7500, "large": 9000, "small": 5000},
        # Looser confidence thresholds because ships are farther from the hydrophone
        "confidence_thresholds": {
            "high":   {"ratio": 2.0,  "delta_L": 4},
            "medium": {"ratio": 0.2,  "delta_L": -2},
            "low":    {"ratio": 0.05, "delta_L": -8},
        },
    },
]

# Derived lookups — built once from SITES above
COLLECT_SLUGS        = [s["slug"]      for s in SITES]   # kebab, for aisstream/collect
PROCESS_KEYS         = [s["key"]       for s in SITES]   # underscore, for processing
KEY_TO_S3            = {s["key"]: s["s3_prefix"]    for s in SITES}
KEY_TO_HLS           = {s["key"]: s["hls_prefix"]   for s in SITES}
KEY_TO_DATA_DIR      = {s["key"]: f"{s['key']}_data" for s in SITES}
CPA_OVERRIDES        = {s["key"]: s["cpa_overrides"]         for s in SITES if s["cpa_overrides"]}
CONFIDENCE_THRESHOLDS = {s["key"]: s["confidence_thresholds"] for s in SITES if s["confidence_thresholds"]}
