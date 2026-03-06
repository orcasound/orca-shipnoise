"""
Unit tests for get_latest_timestamp.py
Tests staleness detection for hydrophone monitoring.
"""
import datetime
import pytest
from unittest.mock import patch
from get_latest_timestamp import export_latest_complete_for_site, STALE_THRESHOLD_DAYS


class TestStalenessWarning:
    def test_fresh_timestamps_no_warning(self, capsys, tmp_path):
        today = datetime.date.today().isoformat()
        mock_lines = [f"key,{today}T00:00:00+00:00,{today}T00:00:10+00:00"]

        with patch("get_latest_timestamp.pick_latest_complete_folder", return_value="123"), \
             patch("get_latest_timestamp.export_timestamp_for_prefix", return_value=(mock_lines, today)), \
             patch("get_latest_timestamp.OUTPUT_ROOT", str(tmp_path)):
            export_latest_complete_for_site("bush_point", "rpi_bush_point/hls/")

        captured = capsys.readouterr()
        assert "WARNING" not in captured.out

    def test_stale_timestamps_prints_warning(self, capsys, tmp_path):
        stale_date = (datetime.date.today() - datetime.timedelta(days=47)).isoformat()
        mock_lines = [f"key,{stale_date}T00:00:00+00:00,{stale_date}T00:00:10+00:00"]

        with patch("get_latest_timestamp.pick_latest_complete_folder", return_value="123"), \
             patch("get_latest_timestamp.export_timestamp_for_prefix", return_value=(mock_lines, stale_date)), \
             patch("get_latest_timestamp.OUTPUT_ROOT", str(tmp_path)):
            export_latest_complete_for_site("bush_point", "rpi_bush_point/hls/")

        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "bush_point" in captured.out
        assert "Hydrophone may be offline" in captured.out

    def test_exactly_at_threshold_no_warning(self, capsys, tmp_path):
        threshold_date = (datetime.date.today() - datetime.timedelta(days=STALE_THRESHOLD_DAYS)).isoformat()
        mock_lines = [f"key,{threshold_date}T00:00:00+00:00,{threshold_date}T00:00:10+00:00"]

        with patch("get_latest_timestamp.pick_latest_complete_folder", return_value="123"), \
             patch("get_latest_timestamp.export_timestamp_for_prefix", return_value=(mock_lines, threshold_date)), \
             patch("get_latest_timestamp.OUTPUT_ROOT", str(tmp_path)):
            export_latest_complete_for_site("bush_point", "rpi_bush_point/hls/")

        captured = capsys.readouterr()
        assert "WARNING" not in captured.out

    def test_one_day_past_threshold_warns(self, capsys, tmp_path):
        stale_date = (datetime.date.today() - datetime.timedelta(days=STALE_THRESHOLD_DAYS + 1)).isoformat()
        mock_lines = [f"key,{stale_date}T00:00:00+00:00,{stale_date}T00:00:10+00:00"]

        with patch("get_latest_timestamp.pick_latest_complete_folder", return_value="123"), \
             patch("get_latest_timestamp.export_timestamp_for_prefix", return_value=(mock_lines, stale_date)), \
             patch("get_latest_timestamp.OUTPUT_ROOT", str(tmp_path)):
            export_latest_complete_for_site("bush_point", "rpi_bush_point/hls/")

        captured = capsys.readouterr()
        assert "WARNING" in captured.out
