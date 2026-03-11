"""
Unit tests for ais_to_transits.py
Tests geometry helpers and time parsing.
"""
import math
import pytest
from ais_to_transits import haversine, compute_bearing, parse_time


class TestHaversine:
    def test_same_point_is_zero(self):
        assert haversine(48.0, -122.0, 48.0, -122.0) == 0.0

    def test_known_distance(self):
        # Bush Point to Orcasound Lab is ~72 km apart
        dist = haversine(48.0336664, -122.6040035, 48.5583362, -123.1735774)
        assert 65_000 < dist < 80_000

    def test_symmetry(self):
        d1 = haversine(48.0, -122.0, 49.0, -123.0)
        d2 = haversine(49.0, -123.0, 48.0, -122.0)
        assert abs(d1 - d2) < 1  # within 1 metre

    def test_one_degree_latitude_approx_111km(self):
        dist = haversine(0.0, 0.0, 1.0, 0.0)
        assert 110_000 < dist < 112_000


class TestComputeBearing:
    def test_due_north(self):
        # Moving straight north
        bearing = compute_bearing(0.0, 0.0, 1.0, 0.0)
        assert abs(bearing - 0.0) < 1.0

    def test_due_east(self):
        bearing = compute_bearing(0.0, 0.0, 0.0, 1.0)
        assert abs(bearing - 90.0) < 1.0

    def test_due_south(self):
        bearing = compute_bearing(1.0, 0.0, 0.0, 0.0)
        assert abs(bearing - 180.0) < 1.0

    def test_due_west(self):
        bearing = compute_bearing(0.0, 1.0, 0.0, 0.0)
        assert abs(bearing - 270.0) < 1.0

    def test_result_in_0_360_range(self):
        bearing = compute_bearing(48.0, -122.0, 47.0, -123.0)
        assert 0.0 <= bearing < 360.0


class TestParseTime:
    def test_standard_format(self):
        dt = parse_time("2024-01-15 10:30:00")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15

    def test_with_microseconds(self):
        dt = parse_time("2024-01-15 10:30:00.123456")
        assert dt is not None
        assert dt.second == 0

    def test_with_utc_suffix(self):
        dt = parse_time("2024-01-15 10:30:00 UTC")
        assert dt is not None

    def test_empty_string_returns_none(self):
        assert parse_time("") is None

    def test_none_returns_none(self):
        assert parse_time(None) is None

    def test_invalid_string_returns_none(self):
        assert parse_time("not-a-date") is None
