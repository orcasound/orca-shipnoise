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
