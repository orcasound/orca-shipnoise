"""
Unit tests for extract_loudest_segment.py
Tests segment range parsing and confidence classification.
"""
import pytest
from extract_loudest_segment import parse_segment_ranges, classify_confidence


class TestParseSegmentRanges:
    def test_single_range(self):
        result = parse_segment_ranges("1539203407/live004-live006")
        assert len(result) == 1
        assert result[0]["folder"] == "1539203407"
        assert result[0]["start"] == 4
        assert result[0]["end"] == 6

    def test_multiple_ranges(self):
        result = parse_segment_ranges("1539203407/live004-live006, 1539203407/live010-live012")
        assert len(result) == 2

    def test_empty_string_returns_empty(self):
        result = parse_segment_ranges("")
        assert result == []

    def test_invalid_format_returns_empty(self):
        result = parse_segment_ranges("not-a-segment")
        assert result == []

    def test_reversed_range_is_corrected(self):
        # start > end should be swapped
        result = parse_segment_ranges("1539203407/live010-live004")
        assert result[0]["start"] == 4
        assert result[0]["end"] == 10

    def test_em_dash_separator(self):
        # Some sources use em-dash instead of hyphen
        result = parse_segment_ranges("1539203407/live004–live006")
        assert len(result) == 1


class TestClassifyConfidence:
    def test_high_confidence_high_ratio(self):
        assert classify_confidence(ratio=6.0) == "high"

    def test_medium_confidence(self):
        assert classify_confidence(ratio=1.0) == "medium"

    def test_low_ratio_returns_none(self):
        assert classify_confidence(ratio=0.05) == "none"

    def test_nan_ratio_returns_none(self):
        import numpy as np
        assert classify_confidence(ratio=np.nan) == "none"

    def test_delta_L_boosts_to_high(self):
        # Low ratio but high delta_L should push to high
        assert classify_confidence(ratio=0.1, delta_L=7.0) == "high"

    def test_sunset_bay_lower_thresholds(self):
        # Sunset Bay has lower thresholds
        assert classify_confidence(ratio=2.5, site_name="Sunset_Bay") == "high"
        assert classify_confidence(ratio=0.3, site_name="Sunset_Bay") == "medium"

    def test_sunset_bay_nan_returns_none(self):
        import numpy as np
        assert classify_confidence(ratio=np.nan, site_name="Sunset_Bay") == "none"
