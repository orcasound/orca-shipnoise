"""
Unit tests for get_latest_timestamp.py
Tests staleness detection for hydrophone monitoring.
"""
import datetime
import pytest
from unittest.mock import patch
from preprocess.get_latest_timestamp import export_for_date, STALE_THRESHOLD_DAYS


def make_folder_id(target_date):
    """Return a Unix timestamp string for noon UTC on target_date."""
    dt = datetime.datetime.combine(target_date, datetime.time(12, 0), tzinfo=datetime.timezone.utc)
    return str(int(dt.timestamp()))


class TestStalenessWarning:
    def test_fresh_timestamps_no_warning(self, capsys, tmp_path):
        today = datetime.date.today()
        folder_id = make_folder_id(today)
        mock_lines = [f"key,{today.isoformat()}T00:00:00+00:00,{today.isoformat()}T00:00:10+00:00"]

        with patch("preprocess.get_latest_timestamp.list_numeric_subfolders", return_value=[folder_id]), \
             patch("preprocess.get_latest_timestamp.fetch_timestamps_for_folder", return_value=mock_lines), \
             patch("preprocess.get_latest_timestamp.OUTPUT_ROOT", str(tmp_path)):
            export_for_date("bush_point", "rpi_bush_point/hls/", today)

        captured = capsys.readouterr()
        assert "WARNING" not in captured.out

    def test_stale_timestamps_prints_warning(self, capsys, tmp_path):
        stale_date = datetime.date.today() - datetime.timedelta(days=47)
        folder_id = make_folder_id(stale_date)
        mock_lines = [f"key,{stale_date.isoformat()}T00:00:00+00:00,{stale_date.isoformat()}T00:00:10+00:00"]

        with patch("preprocess.get_latest_timestamp.list_numeric_subfolders", return_value=[folder_id]), \
             patch("preprocess.get_latest_timestamp.fetch_timestamps_for_folder", return_value=mock_lines), \
             patch("preprocess.get_latest_timestamp.OUTPUT_ROOT", str(tmp_path)):
            export_for_date("bush_point", "rpi_bush_point/hls/", stale_date)

        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "bush_point" in captured.out
        assert "Hydrophone may be offline" in captured.out

    def test_exactly_at_threshold_no_warning(self, capsys, tmp_path):
        threshold_date = datetime.date.today() - datetime.timedelta(days=STALE_THRESHOLD_DAYS)
        folder_id = make_folder_id(threshold_date)
        mock_lines = [f"key,{threshold_date.isoformat()}T00:00:00+00:00,{threshold_date.isoformat()}T00:00:10+00:00"]

        with patch("preprocess.get_latest_timestamp.list_numeric_subfolders", return_value=[folder_id]), \
             patch("preprocess.get_latest_timestamp.fetch_timestamps_for_folder", return_value=mock_lines), \
             patch("preprocess.get_latest_timestamp.OUTPUT_ROOT", str(tmp_path)):
            export_for_date("bush_point", "rpi_bush_point/hls/", threshold_date)

        captured = capsys.readouterr()
        assert "WARNING" not in captured.out

    def test_one_day_past_threshold_warns(self, capsys, tmp_path):
        stale_date = datetime.date.today() - datetime.timedelta(days=STALE_THRESHOLD_DAYS + 1)
        folder_id = make_folder_id(stale_date)
        mock_lines = [f"key,{stale_date.isoformat()}T00:00:00+00:00,{stale_date.isoformat()}T00:00:10+00:00"]

        with patch("preprocess.get_latest_timestamp.list_numeric_subfolders", return_value=[folder_id]), \
             patch("preprocess.get_latest_timestamp.fetch_timestamps_for_folder", return_value=mock_lines), \
             patch("preprocess.get_latest_timestamp.OUTPUT_ROOT", str(tmp_path)):
            export_for_date("bush_point", "rpi_bush_point/hls/", stale_date)

        captured = capsys.readouterr()
        assert "WARNING" in captured.out
