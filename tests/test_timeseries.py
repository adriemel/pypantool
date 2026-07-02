"""Tests for core/timeseries.py."""

from pathlib import Path

import pytest

from core.timeseries import (
    FORMAT_ERROR_LINE,
    extract_interval_lines,
    find_datetime_column,
)

FIXTURE = Path(__file__).parent / "fixtures" / "test_timeseries.txt"


def _load() -> list[str]:
    with open(FIXTURE, encoding="UTF-8") as fh:
        return [line.rstrip("\n") for line in fh]


ALL_LINES = _load()


class TestFindDatetimeColumn:
    def test_finds_column(self):
        assert find_datetime_column(ALL_LINES[0]) == 1

    def test_missing_column(self):
        assert find_datetime_column("Station\tDepth\tTemp") == -1

    def test_case_insensitive(self):
        assert find_datetime_column("a\tDATE/TIME [UTC]\tb") == 1


class TestExtractIntervalLines:
    def test_default_interval(self):
        result = list(extract_interval_lines(ALL_LINES))
        # header, 08:00 (first), 08:10 (+600s), error marker for the malformed
        # cell, 08:20:30.5 (+630s), 08:21 (last line, always written)
        assert result == [
            ALL_LINES[0],
            ALL_LINES[1],
            ALL_LINES[3],
            FORMAT_ERROR_LINE,
            ALL_LINES[6],
            ALL_LINES[7],
        ]

    def test_skip_header(self):
        result = list(extract_interval_lines(ALL_LINES, keep_header=False))
        assert result[0] == ALL_LINES[1]

    def test_larger_interval(self):
        result = list(extract_interval_lines(ALL_LINES, interval_seconds=1800))
        # Only the first line qualifies; malformed still errors; last always kept.
        assert result == [
            ALL_LINES[0],
            ALL_LINES[1],
            FORMAT_ERROR_LINE,
            ALL_LINES[7],
        ]

    def test_last_line_always_written(self):
        result = list(extract_interval_lines(ALL_LINES, interval_seconds=10_000_000))
        assert result[-1] == ALL_LINES[7]

    def test_no_datetime_column_raises(self):
        with pytest.raises(ValueError, match="Date/Time"):
            list(extract_interval_lines(["Station\tDepth", "PS001\t10"]))

    def test_invalid_interval_raises(self):
        with pytest.raises(ValueError, match="positive"):
            list(extract_interval_lines(ALL_LINES, interval_seconds=0))

    def test_empty_input(self):
        assert list(extract_interval_lines([])) == []

    def test_header_only(self):
        assert list(extract_interval_lines([ALL_LINES[0]])) == [ALL_LINES[0]]
