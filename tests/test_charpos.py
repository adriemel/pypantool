"""Tests for core/charpos.py."""

from pathlib import Path

import pytest

from core.charpos import insert_at_positions, parse_positions, replace_at_positions

FIXTURE = Path(__file__).parent / "fixtures" / "test_data.txt"


def _load() -> list[str]:
    with open(FIXTURE, encoding="UTF-8") as fh:
        return [line.rstrip("\n") for line in fh]


ALL_LINES = _load()


class TestParsePositions:
    def test_single(self):
        assert parse_positions("5") == [4]

    def test_list_and_range(self):
        assert parse_positions("1, 3-5") == [0, 2, 3, 4]

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_positions("  ")

    def test_zero_raises(self):
        with pytest.raises(ValueError):
            parse_positions("0")

    def test_reversed_range_raises(self):
        with pytest.raises(ValueError):
            parse_positions("5-3")

    def test_non_integer_raises(self):
        with pytest.raises(ValueError):
            parse_positions("a")


class TestInsertAtPositions:
    def test_insert_at_start(self):
        result = list(insert_at_positions(ALL_LINES, "1", ">"))
        assert all(out == ">" + orig for out, orig in zip(result, ALL_LINES))

    def test_insert_two_positions(self):
        result = list(insert_at_positions(["abcdef"], "3,5", "-"))
        assert result == ["ab-cd-ef"]

    def test_position_past_end_appends(self):
        result = list(insert_at_positions(["ab"], "10", "X"))
        assert result == ["abX"]

    def test_line_count_unchanged(self):
        assert len(list(insert_at_positions(ALL_LINES, "2", "#"))) == len(ALL_LINES)


class TestReplaceAtPositions:
    def test_replace_first_char(self):
        result = list(replace_at_positions(["abcdef"], "1", "X"))
        assert result == ["Xbcdef"]

    def test_replace_range(self):
        result = list(replace_at_positions(["abcdef"], "2-4", "_"))
        assert result == ["a___ef"]

    def test_empty_text_deletes(self):
        result = list(replace_at_positions(["abcdef"], "2,4", ""))
        assert result == ["acef"]

    def test_position_past_end_appends(self):
        result = list(replace_at_positions(["ab"], "10", "X"))
        assert result == ["abX"]

    def test_fixture_first_char(self):
        result = list(replace_at_positions(ALL_LINES, "1", "@"))
        assert all(out == "@" + orig[1:] for out, orig in zip(result, ALL_LINES))
