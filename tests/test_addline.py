"""Tests for core/addline.py."""

from pathlib import Path

import pytest

from core.addline import add_lines

FIXTURE = Path(__file__).parent / "fixtures" / "test_data.txt"


def _load() -> list[str]:
    with open(FIXTURE, encoding="UTF-8") as fh:
        return [line.rstrip("\n") for line in fh]


ALL_LINES = _load()


class TestAddLines:
    def test_insert_at_top(self):
        result = list(add_lines(["a", "b"], ["new"], line_no=1))
        assert result == ["new", "a", "b"]

    def test_insert_in_middle(self):
        result = list(add_lines(["a", "b", "c"], ["new"], line_no=2))
        assert result == ["a", "new", "b", "c"]

    def test_insert_block(self):
        result = list(add_lines(["a", "b"], ["x", "y"], line_no=2))
        assert result == ["a", "x", "y", "b"]

    def test_beyond_end_appends(self):
        result = list(add_lines(["a", "b"], ["new"], line_no=99))
        assert result == ["a", "b", "new"]

    def test_empty_input_appends(self):
        assert list(add_lines([], ["new"])) == ["new"]

    def test_fixture_line_count(self):
        result = list(add_lines(ALL_LINES, ["x", "y"], line_no=5))
        assert len(result) == len(ALL_LINES) + 2
        assert result[4] == "x"
        assert result[5] == "y"

    def test_line_no_zero_raises(self):
        with pytest.raises(ValueError, match="1 or greater"):
            list(add_lines(["a"], ["x"], line_no=0))

    def test_empty_text_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            list(add_lines(["a"], []))
