"""
Centralized site configuration for the shipnoise pipeline.

Adding or removing a site only requires a change here.
"""

SITES = [
    {
        "slug":          "bush-point",           # kebab-case (aisstream, collect)
        "key":           "bush_point",            # underscore (processing, dirs)
        "s3_prefix":     "rpi_bush_point",        # S3 bucket prefix
        "hls_prefix":    "rpi_bush_point/hls/",   # S3 HLS prefix
        "cpa_overrides": None,                    # use global defaults
    },
    {
        "slug":          "orcasound-lab",
        "key":           "orcasound_lab",
        "s3_prefix":     "rpi_orcasound_lab",
        "hls_prefix":    "rpi_orcasound_lab/hls/",
        "cpa_overrides": None,
    },
    {
        "slug":          "port-townsend",
        "key":           "port_townsend",
        "s3_prefix":     "rpi_port_townsend",
        "hls_prefix":    "rpi_port_townsend/hls/",
        "cpa_overrides": None,
    },
    {
        "slug":          "sunset-bay",
        "key":           "sunset_bay",
        "s3_prefix":     "rpi_sunset_bay",
        "hls_prefix":    "rpi_sunset_bay/hls/",
        # Sunset Bay ships are routinely detected 6-8 km out, so widen the gates
        "cpa_overrides": {"default": 7500, "large": 9000, "small": 5000},
    },
]

# Derived lookups — built once from SITES above
COLLECT_SLUGS   = [s["slug"]      for s in SITES]   # kebab, for aisstream/collect
PROCESS_KEYS    = [s["key"]       for s in SITES]   # underscore, for processing
KEY_TO_S3       = {s["key"]: s["s3_prefix"]    for s in SITES}
KEY_TO_HLS      = {s["key"]: s["hls_prefix"]   for s in SITES}
KEY_TO_DATA_DIR = {s["key"]: f"{s['key']}_data" for s in SITES}
CPA_OVERRIDES   = {s["key"]: s["cpa_overrides"] for s in SITES if s["cpa_overrides"]}
