"""Tests for core/rename.py."""

import pytest
from pathlib import Path

from core.rename import apply_rename, preview_renames


class TestApplyRename:
    def test_no_ops_returns_original(self):
        assert apply_rename("data.tab") == "data.tab"

    def test_search_replace(self):
        assert apply_rename("old_data.tab", search="old_", replace="new_") == "new_data.tab"

    def test_search_replace_multiple_occurrences(self):
        assert apply_rename("aa_aa.tab", search="aa", replace="bb") == "bb_bb.tab"

    def test_search_replace_empty_replace_deletes(self):
        assert apply_rename("data_v1.tab", search="_v1", replace="") == "data.tab"

    def test_prefix(self):
        assert apply_rename("data.tab", prefix="station_") == "station_data.tab"

    def test_suffix_before_extension(self):
        assert apply_rename("data.tab", suffix="_v2") == "data_v2.tab"

    def test_suffix_no_extension(self):
        assert apply_rename("data", suffix="_v2") == "data_v2"

    def test_all_ops_applied_in_order(self):
        # search/replace first, then prefix, then suffix
        result = apply_rename("old.tab", search="old", replace="new", prefix="pre_", suffix="_suf")
        assert result == "pre_new_suf.tab"

    def test_search_not_found_unchanged(self):
        assert apply_rename("data.tab", search="xyz", replace="abc") == "data.tab"

    def test_empty_search_ignored(self):
        assert apply_rename("data.tab", search="", replace="abc") == "data.tab"


class TestPreviewRenames:
    def test_returns_pairs(self, tmp_path):
        f1 = tmp_path / "data.tab"
        f2 = tmp_path / "other.tab"
        pairs = preview_renames([f1, f2], prefix="pre_")
        assert pairs == [
            (f1, tmp_path / "pre_data.tab"),
            (f2, tmp_path / "pre_other.tab"),
        ]

    def test_unchanged_files_have_same_old_and_new(self, tmp_path):
        f = tmp_path / "data.tab"
        pairs = preview_renames([f])
        assert pairs == [(f, f)]

    def test_filesystem_not_modified(self, tmp_path):
        f = tmp_path / "data.tab"
        f.write_text("x")
        preview_renames([f], prefix="new_")
        assert f.exists()
        assert not (tmp_path / "new_data.tab").exists()

    def test_empty_list(self):
        assert preview_renames([]) == []
