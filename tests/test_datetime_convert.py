"""Tests for core.datetime_convert."""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.datetime_convert import convert_datetime, format_iso, make_parser

FIXTURE = Path(__file__).parent / "fixtures" / "test_datetime_formats.txt"
LINES = FIXTURE.read_text(encoding="utf-8").splitlines()


def _col(result: list[str], index: int) -> list[str]:
    return [line.split("\t")[index] for line in result if "\t" in line]


class TestMakeParser:
    @pytest.mark.parametrize("fmt, text, expected, precision", [
        ("dd.MM.yyyy HH:mm:ss", "15.01.2024 08:20:05", datetime(2024, 1, 15, 8, 20, 5), "second"),
        ("d.M.yyyy H:mm", "1.3.2024 7:05", datetime(2024, 3, 1, 7, 5), "minute"),
        ("MM/dd/yy", "03/01/24", datetime(2024, 3, 1), "date"),
        ("yyyyMMdd HHmmss", "20240115 082005", datetime(2024, 1, 15, 8, 20, 5), "second"),
        ("yyyy DDD HH:mm", "2024 60 12:00", datetime(2024, 2, 29, 12), "minute"),
        ("dd-MMM-yyyy", "05-mar-2024", datetime(2024, 3, 5), "date"),
        ("M/d/yyyy h:mm:ss AP", "3/1/2024 12:05:00 AM", datetime(2024, 3, 1, 0, 5), "second"),
        ("yyyy-MM-dd HH:mm:ss.zzz", "2024-01-15 08:20:05.25", datetime(2024, 1, 15, 8, 20, 5, 250000), "milli"),
        ("yyyy-MM-dd'T'HH'h'mm", "2024-01-15T08h20", datetime(2024, 1, 15, 8, 20), "minute"),
    ])
    def test_patterns(self, fmt, text, expected, precision):
        parse, got_precision = make_parser(fmt)
        assert parse(text) == expected
        assert got_precision == precision

    @pytest.mark.parametrize("fmt, text", [
        ("dd.MM.yyyy", "31.02.2024"), ("dd.MM.yyyy", "1.3.2024"),
        ("dd.MM.yyyy", "2024-03-02"), ("yyyy DDD", "2023 366"), ("excel", "1,5"),
    ])
    def test_rejects(self, fmt, text):
        assert make_parser(fmt)[0](text) is None

    def test_excel_and_unix(self):
        assert make_parser("excel")[0]("45306.3333333333") == datetime(2024, 1, 15, 8)
        assert make_parser("unix")[0]("1705305600") == datetime(2024, 1, 15, 8)

    @pytest.mark.parametrize("fmt", ["", "dd.MM", "yyyy-MM", "yyyy-MM-dd mm", "dd.dd.yyyy", "yyyy 'x"])
    def test_invalid_formats(self, fmt):
        with pytest.raises(ValueError):
            make_parser(fmt)

    def test_format_iso(self):
        stamp = datetime(2024, 1, 5, 8, 2, 3, 45000)
        assert format_iso(stamp, "date") == "2024-01-05"
        assert format_iso(stamp, "minute") == "2024-01-05T08:02"
        assert format_iso(stamp, "milli") == "2024-01-05T08:02:03.045"


class TestConvertDatetime:
    def test_merge_date_and_time(self):
        fails: list[tuple[int, str]] = []
        result = list(convert_datetime(LINES, 2, "d.M.yyyy HH:mm:ss", time_column=3,
                                       on_fail=lambda n, t: fails.append((n, t))))
        assert result[0] == "Station\tDate/Time\tExcel day\tTemp [°C]"
        assert result[3] == "// comment line"
        assert _col(result, 1)[1:] == [
            "2024-01-15T08:00:00", "2024-01-15T23:30:15", "2024-03-01T00:05:00",
            "", "2024-03-02 12:00:00", "2024-12-31T23:59:59",
        ]
        assert fails == [(7, "2024-03-02 12:00:00")]
        assert len(result) == len(LINES)

    def test_excel_serial_matches_text_dates(self):
        result = list(convert_datetime(LINES, 4, "excel"))
        assert result[0].split("\t")[3] == "Date/Time"
        assert _col(result, 3)[1:] == [
            "2024-01-15T08:00:00", "2024-01-15T23:30:15", "2024-03-01T00:05:00",
            "", "n.d.", "2024-12-31T23:59:59",
        ]

    def test_utc_offset_crosses_midnight(self):
        result = list(convert_datetime(LINES, 2, "d.M.yyyy HH:mm:ss", time_column=3,
                                       utc_offset_hours=1))
        assert _col(result, 1)[1:4] == [
            "2024-01-15T07:00:00", "2024-01-15T22:30:15", "2024-02-29T23:05:00",
        ]

    def test_keep_original_inserts_column(self):
        result = list(convert_datetime(LINES, 2, "d.M.yyyy", keep_original=True))
        assert result[0] == "Station\tDate/Time\tDate\tTime\tExcel day\tTemp [°C]"
        assert result[1].split("\t")[1:3] == ["2024-01-15", "15.01.2024"]
        assert result[6].split("\t")[1:3] == ["", "2024-03-02"]

    def test_wrong_format_aborts(self):
        many = [LINES[0]] + [LINES[1]] * 150
        with pytest.raises(ValueError, match="None of the first"):
            list(convert_datetime(many, 2, "MM/dd/yyyy"))

    def test_invalid_arguments(self):
        with pytest.raises(ValueError, match="does not exist"):
            list(convert_datetime(LINES, 9, "dd.MM.yyyy"))
        with pytest.raises(ValueError, match="different column"):
            list(convert_datetime(LINES, 2, "dd.MM.yyyy", time_column=2))
        with pytest.raises(ValueError, match="UTC offset"):
            list(convert_datetime(LINES, 2, "dd.MM.yyyy", utc_offset_hours=2))

    def test_empty_input(self):
        assert list(convert_datetime([], 1, "dd.MM.yyyy")) == []
