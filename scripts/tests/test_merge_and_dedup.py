"""
Unit tests for merge_and_dedup.py
Tests acoustic relevance filtering logic.
"""
import numpy as np
import pytest
from merge_and_dedup import is_acoustically_relevant


def make_row(cpa_distance_m, length_m=None, site_name=None):
    return {
        "cpa_distance_m": cpa_distance_m,
        "length_m": length_m,
        "site_name": site_name or "",
    }


class TestIsAcousticallyRelevant:
    def test_normal_ship_within_range(self):
        row = make_row(cpa_distance_m=4000, length_m=100)
        assert is_acoustically_relevant(row) is True

    def test_normal_ship_too_far(self):
        row = make_row(cpa_distance_m=6000, length_m=100)
        assert is_acoustically_relevant(row) is False

    def test_large_ship_within_extended_range(self):
        # Ships >150m get a wider gate (8000m)
        row = make_row(cpa_distance_m=7000, length_m=200)
        assert is_acoustically_relevant(row) is True

    def test_large_ship_too_far(self):
        row = make_row(cpa_distance_m=9000, length_m=200)
        assert is_acoustically_relevant(row) is False

    def test_small_ship_within_range(self):
        # Ships <50m have tighter gate (3000m)
        row = make_row(cpa_distance_m=2500, length_m=30)
        assert is_acoustically_relevant(row) is True

    def test_small_ship_too_far(self):
        row = make_row(cpa_distance_m=4000, length_m=30)
        assert is_acoustically_relevant(row) is False

    def test_nan_cpa_is_irrelevant(self):
        row = make_row(cpa_distance_m=np.nan)
        assert is_acoustically_relevant(row) is False

    def test_sunset_bay_wider_gate(self):
        # Sunset Bay override: default 7500m
        row = make_row(cpa_distance_m=7000, length_m=100, site_name="sunset_bay_data")
        assert is_acoustically_relevant(row) is True

    def test_unknown_length_uses_default(self):
        row = make_row(cpa_distance_m=4500, length_m=None)
        assert is_acoustically_relevant(row) is True

    def test_boundary_exactly_at_limit(self):
        row = make_row(cpa_distance_m=5000, length_m=100)
        assert is_acoustically_relevant(row) is True
