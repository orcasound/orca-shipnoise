"""
Integration tests for the merge_and_dedup pipeline step.
Uses pytest's tmp_path fixture to simulate the Sites/ directory structure
without touching the real filesystem or any external services.
"""
import os
import pandas as pd
import pytest


@pytest.fixture
def sites_dir(tmp_path):
    """Create a fake Sites/ directory with one site and one day of data."""
    site_dir = tmp_path / "bush_point_data"
    transits_dir = site_dir / "20240115_transits_filtered"
    output_dir = site_dir / "20240115_output"
    transits_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    # Write a minimal _windowed.csv (output of match_all_transits_to_ts)
    df = pd.DataFrame([
        {
            "mmsi": "123456789",
            "shipname": "TEST VESSEL",
            "t_cpa": "2024-01-15T10:00:00Z",
            "cpa_distance_m": 3000.0,
            "length_m": 120.0,
            "width_m": 20.0,
            "match_status": "window_found",
            "segment_count": 3,
            "segment_range": "1705312800/live010-live012",
            "site_name": "bush-point",
        },
        {
            "mmsi": "999999999",
            "shipname": "FAR AWAY SHIP",
            "t_cpa": "2024-01-15T11:00:00Z",
            "cpa_distance_m": 20000.0,  # too far, should be filtered out
            "length_m": 80.0,
            "width_m": 15.0,
            "match_status": "window_found",
            "segment_count": 2,
            "segment_range": "1705316400/live005-live006",
            "site_name": "bush-point",
        },
    ])
    csv_path = transits_dir / "20240115_ais_raw_windowed.csv"
    df.to_csv(csv_path, index=False)

    return tmp_path


def test_merge_and_dedup_filters_far_ships(sites_dir, monkeypatch):
    """Ships beyond CPA threshold should be removed from output."""
    import merge_and_dedup

    monkeypatch.setattr(merge_and_dedup, "SITES_DIR", str(sites_dir))

    merge_and_dedup.process_site("bush_point_data", target_dates=["20240115"])

    output_csv = sites_dir / "bush_point_data" / "20240115_output" / "20240115_windowed_merged.csv"
    assert output_csv.exists(), "Output CSV was not created"

    result = pd.read_csv(output_csv)
    assert len(result) == 1, "Only 1 vessel should pass the distance filter"
    assert result.iloc[0]["shipname"] == "TEST VESSEL"


def test_merge_and_dedup_creates_output_dir(sites_dir, monkeypatch):
    """Output directory should be created if it doesn't exist."""
    import merge_and_dedup

    monkeypatch.setattr(merge_and_dedup, "SITES_DIR", str(sites_dir))

    # Remove the output dir to verify it gets re-created
    output_dir = sites_dir / "bush_point_data" / "20240115_output"
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)

    merge_and_dedup.process_site("bush_point_data", target_dates=["20240115"])

    assert output_dir.exists()


def test_merge_and_dedup_deduplicates_same_mmsi(sites_dir, monkeypatch):
    """Duplicate MMSI entries should be deduplicated, keeping closest CPA."""
    import merge_and_dedup
    import shutil

    monkeypatch.setattr(merge_and_dedup, "SITES_DIR", str(sites_dir))

    transits_dir = sites_dir / "bush_point_data" / "20240115_transits_filtered"

    # Add a second CSV with a duplicate MMSI but farther CPA
    df_dup = pd.DataFrame([
        {
            "mmsi": "123456789",
            "shipname": "TEST VESSEL",
            "t_cpa": "2024-01-15T12:00:00Z",
            "cpa_distance_m": 4500.0,  # farther than the 3000m in the first file
            "length_m": 120.0,
            "width_m": 20.0,
            "match_status": "window_found",
            "segment_count": 3,
            "segment_range": "1705320000/live020-live022",
            "site_name": "bush-point",
        }
    ])
    df_dup.to_csv(transits_dir / "20240115_ais_raw2_windowed.csv", index=False)

    merge_and_dedup.process_site("bush_point_data", target_dates=["20240115"])

    output_csv = sites_dir / "bush_point_data" / "20240115_output" / "20240115_windowed_merged.csv"
    result = pd.read_csv(output_csv)

    # Only 1 row for MMSI 123456789 — closest CPA wins
    vessel_rows = result[result["mmsi"] == 123456789]
    assert len(vessel_rows) == 1
    assert vessel_rows.iloc[0]["cpa_distance_m"] == 3000.0
