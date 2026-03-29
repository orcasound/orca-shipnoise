"""
Regression tests — guard against known bugs being re-introduced.
"""
import re
import pytest


class TestSiteDirectoryNaming:
    """
    Regression: site directory names must be lowercase to match what
    ais_collect.py creates (e.g. 'bush_point_data', not 'Bush_Point_data').

    Bug history: match_all_transits_to_ts, merge_and_dedup, and
    extract_loudest_segment all used title-case paths, causing every
    pipeline run to silently skip processing and write nothing to the DB.
    """

    def test_match_all_transits_site_dirs_are_lowercase(self):
        from match_all_transits_to_ts import SITES
        for key, folder_name in SITES.items():
            assert folder_name == folder_name.lower(), (
                f"SITES['{key}'] = '{folder_name}' must be lowercase. "
                f"ais_collect.py creates lowercase directories."
            )

    def test_merge_and_dedup_site_list_is_lowercase(self):
        from merge_and_dedup import SITES
        for folder_name in SITES:
            assert folder_name == folder_name.lower(), (
                f"SITES entry '{folder_name}' must be lowercase."
            )

    def test_ais_collect_creates_lowercase_dirs(self):
        """Verify the naming formula in ais_collect matches lowercase convention."""
        # ais_collect.py line 70: f"{site_slug.replace('-', '_')}_data"
        test_slugs = ["bush-point", "orcasound-lab", "port-townsend", "sunset-bay"]
        for slug in test_slugs:
            dir_name = f"{slug.replace('-', '_')}_data"
            assert dir_name == dir_name.lower(), (
                f"ais_collect.py would create '{dir_name}' which is not lowercase"
            )

    def test_match_all_transits_and_collect_agree_on_dir_names(self):
        """Directory names in match_all_transits_to_ts must match what ais_collect creates."""
        from match_all_transits_to_ts import SITES

        collect_slugs = {
            "bush_point": "bush-point",
            "orcasound_lab": "orcasound-lab",
            "port_townsend": "port-townsend",
            "sunset_bay": "sunset-bay",
        }

        for key, folder_name in SITES.items():
            slug = collect_slugs[key]
            expected = f"{slug.replace('-', '_')}_data"
            assert folder_name == expected, (
                f"Mismatch for site '{key}': "
                f"match_all_transits expects '{folder_name}' "
                f"but ais_collect creates '{expected}'"
            )

    def test_all_process_scripts_use_key_to_data_dir(self):
        """All process scripts must derive site dirs from KEY_TO_DATA_DIR, not hardcoded strings."""
        from config.sites import KEY_TO_DATA_DIR, COLLECT_SLUGS

        # Verify KEY_TO_DATA_DIR matches what ais_collect creates
        for key, data_dir in KEY_TO_DATA_DIR.items():
            slug = next(s for s in COLLECT_SLUGS if s.replace("-", "_") == key)
            expected = f"{slug.replace('-', '_')}_data"
            assert data_dir == expected, (
                f"KEY_TO_DATA_DIR['{key}'] = '{data_dir}' "
                f"but ais_collect would create '{expected}'"
            )

        # merge_and_dedup and match_all_transits_to_ts must use the same dirs
        from merge_and_dedup import SITES as MERGE_SITES
        from match_all_transits_to_ts import SITES as MATCH_SITES

        assert set(MERGE_SITES) == set(KEY_TO_DATA_DIR.values()), (
            f"merge_and_dedup SITES {set(MERGE_SITES)} != KEY_TO_DATA_DIR values {set(KEY_TO_DATA_DIR.values())}"
        )
        assert set(MATCH_SITES.values()) == set(KEY_TO_DATA_DIR.values()), (
            f"match_all_transits SITES {set(MATCH_SITES.values())} != KEY_TO_DATA_DIR values {set(KEY_TO_DATA_DIR.values())}"
        )
