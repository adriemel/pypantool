"""Tests for core/addcol.py."""

from pathlib import Path

import pytest

from core.addcol import add_column

FIXTURE = Path(__file__).parent / "fixtures" / "test_data.txt"


def _load() -> list[str]:
    with open(FIXTURE, encoding="UTF-8") as fh:
        return [line.rstrip("\n") for line in fh]


ALL_LINES = _load()


class TestAddColumn:
    def test_append_text_column(self):
        result = list(add_column(
            ["H1\tH2", "a\tb", "c\td"],
            header_text="Flag", column_text="ok",
        ))
        assert result == ["H1\tH2\tFlag", "a\tb\tok", "c\td\tok"]

    def test_prepend_text_column(self):
        result = list(add_column(
            ["H1", "a"],
            header_text="Flag", column_text="ok", position="prepend",
        ))
        assert result == ["Flag\tH1", "ok\ta"]

    def test_ordinal_column(self):
        result = list(add_column(
            ["H", "a", "b", "c"],
            add_ordinal=True,
        ))
        assert result == ["No\tH", "1\ta", "2\tb", "3\tc"]

    def test_filename_and_path(self):
        path = Path("/data/station01.tab")
        result = list(add_column(
            ["H", "a"],
            path,
            add_filename=True, add_full_path=True,
        ))
        assert result[0] == "Event label\tFilename\tH"
        assert result[1].startswith("station01\t")
        assert result[1].endswith("station01.tab\ta")

    def test_meta_append(self):
        result = list(add_column(
            ["H", "a"],
            add_ordinal=True, meta_position="append",
        ))
        assert result == ["H\tNo", "a\t1"]

    def test_text_and_meta_combined(self):
        result = list(add_column(
            ["H", "a"],
            header_text="Flag", column_text="ok",
            add_ordinal=True, meta_position="prepend",
        ))
        assert result == ["No\tH\tFlag", "1\ta\tok"]

    def test_fixture_line_count_unchanged(self):
        result = list(add_column(ALL_LINES, header_text="X", column_text="y"))
        assert len(result) == len(ALL_LINES)

    def test_nothing_selected_raises(self):
        with pytest.raises(ValueError, match="Nothing to add"):
            list(add_column(["H", "a"]))

    def test_invalid_position_raises(self):
        with pytest.raises(ValueError, match="position"):
            list(add_column(["H"], header_text="x", position="middle"))

    def test_empty_input(self):
        assert list(add_column([], header_text="x")) == []

    def test_custom_delimiter(self):
        result = list(add_column(
            ["H1;H2", "a;b"],
            header_text="F", column_text="v", delimiter=";",
        ))
        assert result == ["H1;H2;F", "a;b;v"]
