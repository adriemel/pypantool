"""Tests for core.profile (file statistics)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.profile import (
    COLUMN_HEADERS,
    DISTINCT_CAP,
    column_rows,
    format_profile,
    profile_lines,
    summary_rows,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _profile(name: str, **kwargs):
    with open(FIXTURES / name, encoding="utf-8", errors="surrogateescape", newline="") as fh:
        return profile_lines(fh, **kwargs)


def _summary(prof) -> dict[str, tuple[str, bool]]:
    return {label: (text, flag) for label, text, flag in summary_rows(prof)}


class TestMainFixture:
    prof = _profile("test_data.txt")

    def test_structure(self):
        assert self.prof.header_lineno == 4
        assert self.prof.preamble_lines == 3
        assert len(self.prof.columns) == 11
        assert self.prof.empty_lines == 1
        assert self.prof.comment_lines == 1
        assert self.prof.ragged_rows == 0

    def test_numeric_column(self):
        temp = self.prof.columns[5]
        assert temp.name == "Temperature [°C]"
        assert temp.kind == "numeric"
        assert temp.empty == 1
        assert (temp.min_text, temp.max_text) == ("-1.82", "3.85")
        assert (temp.min_decimals, temp.max_decimals) == (2, 2)

    def test_text_column(self):
        station = self.prof.columns[0]
        assert station.kind == "text"
        assert station.distinct == 4

    def test_rows_add_up(self):
        for col in self.prof.columns:
            assert col.filled + col.empty == self.prof.data_rows


class TestPangaeaFixture:
    prof = _profile("test_pangaea_header.txt")

    def test_header_after_metadata_block(self):
        assert self.prof.header_lineno == 6
        assert [c.name for c in self.prof.columns][:2] == ["Event", "Date/Time"]

    def test_marker_not_in_min_max(self):
        temp = self.prof.columns[3]
        assert temp.markers == {"n.d.": 1}
        assert temp.numeric == 3
        assert (temp.min_decimals, temp.max_decimals) == (1, 3)

    def test_short_row_reported(self):
        assert self.prof.ragged_rows == 1
        assert self.prof.ragged_examples == [10]
        assert self.prof.columns[4].empty == 1
        assert _summary(self.prof)["Row width"][1] is True

    def test_report_layout(self):
        report = list(format_profile(self.prof, "x.tab"))
        assert report[0] == "File\tx.tab"
        table = report[report.index("") + 1:]
        assert table[0].split("\t") == COLUMN_HEADERS
        assert len(table) == 1 + 5
        assert all(len(row.split("\t")) == len(COLUMN_HEADERS) for row in table)


class TestTimeseriesFixture:
    prof = _profile("test_timeseries.txt")

    def test_datetime_column(self):
        col = self.prof.columns[1]
        assert col.kind == "date/time"
        assert col.first_time == "2024-01-15T08:00"
        assert col.other == 1
        assert col.other_examples == {"15.01.2024 08:20": 6}
        cells, attention = column_rows(self.prof)[1]
        assert attention and "not ISO 8601" in cells[-1]


class TestFileLevelFindings:
    """Byte-level cases no fixture covers (BOM, CRLF, invalid bytes)."""

    def test_bom_and_mixed_line_endings(self):
        prof = profile_lines(["﻿A\tB\r\n", "1\t2\r\n", "3\t4\n", "5\t6"])
        assert prof.has_bom
        assert prof.columns[0].name == "A"
        assert (prof.crlf, prof.lf, prof.total_lines) == (2, 1, 4)
        assert _summary(prof)["Line endings"][1] is True

    def test_invalid_bytes_reported_not_raised(self):
        raw = "A\tTemp [\xb0C]\n1\t2\n".encode("latin-1")
        lines = raw.decode("utf-8", errors="surrogateescape").splitlines(keepends=True)
        prof = profile_lines(lines)
        assert (prof.invalid_lines, prof.invalid_first_line) == (1, 1)
        assert prof.invalid_first_byte == 0xB0
        text, flag = _summary(prof)["Encoding"]
        assert flag and "0xB0" in text

    def test_no_header(self):
        prof = profile_lines(["a\n", "b\n"])
        assert prof.header_lineno == 0 and prof.columns == []
        assert _summary(prof)["Header"][1] is True

    def test_fill_values_time_order_and_padding(self):
        lines = ["Date/Time\tT\n", "2024-01-01T00:10\t 1.5\n", "2024-01-01T00:10\t-999\n",
                 "2024-01-01T00:00\tNaN\n", "2024-01-01T00:20\t<0.05\n"]
        prof = profile_lines(lines)
        time, temp = prof.columns
        assert (time.time_repeats, time.time_backwards, time.time_backwards_line) == (1, 1, 4)
        assert temp.markers == {"-999": 1, "NaN": 1}
        assert (temp.kind, temp.padded, temp.min_text) == ("mixed", 1, "1.5")
        assert temp.other_examples == {"<0.05": 5}

    def test_distinct_cap(self):
        lines = ["A\tB\n"] + [f"{i}\tx\n" for i in range(DISTINCT_CAP + 5)]
        prof = profile_lines(lines)
        assert prof.columns[0].distinct is None
        assert prof.columns[1].distinct == 1
        assert column_rows(prof)[0][0][9] == f">{DISTINCT_CAP:,}"
