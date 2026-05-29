"""Tests for core/columns.py — run with: python3 -m pytest tests/"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.columns import (
    _make_picker,
    delete_columns,
    delete_matched_columns,
    extract_columns,
    extract_matched_columns,
    parse_column_spec,
)

FIXTURE = Path(__file__).parent / "fixtures" / "test_data.txt"
DELIM = "\t"

# Fixture header (line 4, 0-indexed line 3):
# Station(0) Latitude(1) Longitude(2) Date(3) Depth[m](4) Temperature[°C](5)
# Salinity[PSU](6) Oxygen[ml/l](7) Pressure[dbar](8) Conductivity[mS/cm](9) Comment(10)
TOTAL_COLS = 11
HEADER = (
    "Station\tLatitude\tLongitude\tDate\tDepth [m]\t"
    "Temperature [°C]\tSalinity [PSU]\tOxygen [ml/l]\t"
    "Pressure [dbar]\tConductivity [mS/cm]\tComment"
)


def _load() -> list[str]:
    with open(FIXTURE, encoding="UTF-8") as fh:
        return [line.rstrip("\n") for line in fh]


ALL_LINES = _load()
TOTAL_LINES = 35


# ── parse_column_spec ─────────────────────────────────────────────────────────

class TestParseColumnSpec(unittest.TestCase):
    def test_single(self):
        self.assertEqual(parse_column_spec("1", 11), [0])

    def test_single_end(self):
        self.assertEqual(parse_column_spec("end", 11), [10])

    def test_range(self):
        self.assertEqual(parse_column_spec("1-3", 11), [0, 1, 2])

    def test_end_range(self):
        self.assertEqual(parse_column_spec("5-end", 11), [4, 5, 6, 7, 8, 9, 10])

    def test_comma_list(self):
        self.assertEqual(parse_column_spec("1,3,5", 11), [0, 2, 4])

    def test_mixed(self):
        # "1,3-5,end" with 11 cols → [0, 2, 3, 4, 10]
        self.assertEqual(parse_column_spec("1,3-5,end", 11), [0, 2, 3, 4, 10])

    def test_deduplicates(self):
        # "1-3,2-4" → [0,1,2,3] with no duplicates
        self.assertEqual(parse_column_spec("1-3,2-4", 11), [0, 1, 2, 3])

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            parse_column_spec("", 11)

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            parse_column_spec("abc", 11)

    def test_inverted_range_raises(self):
        with self.assertRaises(ValueError):
            parse_column_spec("5-3", 11)


# ── extract_columns ───────────────────────────────────────────────────────────

class TestExtractColumns(unittest.TestCase):
    def test_single_column(self):
        result = list(extract_columns(ALL_LINES, "1"))
        self.assertEqual(len(result), TOTAL_LINES)
        # Header line (index 3): "Station"
        self.assertEqual(result[3], "Station")
        # First data line (index 4): "PS001"
        self.assertEqual(result[4], "PS001")

    def test_range(self):
        result = list(extract_columns(ALL_LINES, "1-3"))
        self.assertEqual(len(result), TOTAL_LINES)
        self.assertEqual(result[3], "Station\tLatitude\tLongitude")
        # Data line has 3 fields
        fields = result[4].split(DELIM)
        self.assertEqual(len(fields), 3)
        self.assertEqual(fields[0], "PS001")

    def test_end_range(self):
        result = list(extract_columns(ALL_LINES, "10-end"))
        self.assertEqual(len(result), TOTAL_LINES)
        # Header: last 2 columns
        self.assertEqual(result[3], "Conductivity [mS/cm]\tComment")

    def test_comment_lines_pass_through(self):
        result = list(extract_columns(ALL_LINES, "2-3"))
        # First 3 lines are comments with no tabs — passed through unchanged.
        self.assertEqual(result[0], ALL_LINES[0])
        self.assertEqual(result[1], ALL_LINES[1])
        self.assertEqual(result[2], ALL_LINES[2])

    def test_empty_line_passes_through(self):
        result = list(extract_columns(ALL_LINES, "1-3"))
        # Line 17 (index 16) is empty — no delimiter → pass through.
        self.assertEqual(result[16], "")

    def test_empty_input(self):
        self.assertEqual(list(extract_columns([], "1-3")), [])

    def test_only_comment_lines(self):
        lines = ["// comment one", "// comment two"]
        result = list(extract_columns(lines, "1-3"))
        self.assertEqual(result, lines)

    def test_adjacent_spec_all_columns(self):
        # "1-end" should reproduce the original delimited lines unchanged.
        result = list(extract_columns(ALL_LINES, "1-end"))
        # Check a data line is identical to the original.
        self.assertEqual(result[4], ALL_LINES[4])


# ── delete_columns ────────────────────────────────────────────────────────────

class TestDeleteColumns(unittest.TestCase):
    def test_delete_first_column(self):
        result = list(delete_columns(ALL_LINES, "1"))
        # Header now starts with "Latitude"
        self.assertEqual(result[3].split(DELIM)[0], "Latitude")
        # Data line: 10 columns remain
        self.assertEqual(len(result[4].split(DELIM)), TOTAL_COLS - 1)

    def test_delete_range(self):
        result = list(delete_columns(ALL_LINES, "1-3"))
        # Header starts with "Date" (col 4)
        self.assertEqual(result[3].split(DELIM)[0], "Date")
        self.assertEqual(len(result[4].split(DELIM)), TOTAL_COLS - 3)

    def test_delete_last_column(self):
        result = list(delete_columns(ALL_LINES, "end"))
        # Comment column gone; data lines have 10 columns
        self.assertEqual(len(result[4].split(DELIM)), TOTAL_COLS - 1)
        self.assertNotIn("Comment", result[3])

    def test_comment_lines_pass_through(self):
        result = list(delete_columns(ALL_LINES, "1"))
        self.assertEqual(result[0], ALL_LINES[0])
        self.assertEqual(result[2], ALL_LINES[2])

    def test_extract_delete_complement(self):
        # Splitting on columns 1-3: extract gives 3 cols, delete gives 8 cols.
        extracted = list(extract_columns(ALL_LINES, "1-3"))
        deleted = list(delete_columns(ALL_LINES, "1-3"))
        self.assertEqual(len(extracted), len(deleted))
        # Rejoining extracted + deleted fields should reconstruct the original data line.
        e_fields = extracted[4].split(DELIM)
        d_fields = deleted[4].split(DELIM)
        self.assertEqual(len(e_fields) + len(d_fields), TOTAL_COLS)

    def test_empty_input(self):
        self.assertEqual(list(delete_columns([], "1")), [])


# ── extract_matched_columns ───────────────────────────────────────────────────

class TestExtractMatchedColumns(unittest.TestCase):
    def test_single_header_match(self):
        result = list(extract_matched_columns(ALL_LINES, "PSU"))
        # Header: only "Salinity [PSU]"
        self.assertEqual(result[3], "Salinity [PSU]")
        # Data line: single field
        self.assertEqual(len(result[4].split(DELIM)), 1)
        self.assertEqual(result[4], "34.12")

    def test_regex_match(self):
        # Match columns with unit notation: Temperature [°C] and Salinity [PSU]
        result = list(extract_matched_columns(ALL_LINES, r"\[°C\]|\[PSU\]", is_regex=True))
        # Header: two columns
        header_fields = result[3].split(DELIM)
        self.assertEqual(len(header_fields), 2)
        self.assertIn("Temperature [°C]", header_fields)
        self.assertIn("Salinity [PSU]", header_fields)

    def test_pre_header_comments_pass_through(self):
        result = list(extract_matched_columns(ALL_LINES, "Station"))
        # First 3 lines are comments — yielded as-is.
        self.assertEqual(result[0], ALL_LINES[0])
        self.assertEqual(result[1], ALL_LINES[1])
        self.assertEqual(result[2], ALL_LINES[2])

    def test_no_match_returns_empty_rows(self):
        result = list(extract_matched_columns(ALL_LINES, "NOTEXIST"))
        # Header and all data lines become empty strings.
        self.assertEqual(result[3], "")

    def test_match_station_column(self):
        result = list(extract_matched_columns(ALL_LINES, "Station"))
        self.assertEqual(result[3], "Station")
        self.assertEqual(result[4], "PS001")

    def test_empty_input(self):
        self.assertEqual(list(extract_matched_columns([], "Station")), [])


# ── delete_matched_columns ────────────────────────────────────────────────────

class TestDeleteMatchedColumns(unittest.TestCase):
    def test_delete_single_match(self):
        result = list(delete_matched_columns(ALL_LINES, "Comment"))
        # Header has 10 columns now.
        self.assertEqual(len(result[3].split(DELIM)), TOTAL_COLS - 1)
        self.assertNotIn("Comment", result[3])

    def test_delete_regex_match(self):
        # Delete all columns with unit notation [...]
        result = list(delete_matched_columns(ALL_LINES, r"\[.*?\]", is_regex=True))
        # Original header: Station, Latitude, Longitude, Date, Depth[m], Temp[°C],
        # Sal[PSU], Oxy[ml/l], Pressure[dbar], Cond[mS/cm], Comment
        # Columns with []: Depth[m](4), Temp(5), Sal(6), Oxy(7), Pres(8), Cond(9) → 6 removed
        remaining_header = result[3].split(DELIM)
        self.assertEqual(len(remaining_header), TOTAL_COLS - 6)
        self.assertEqual(remaining_header[0], "Station")
        self.assertFalse(any("[" in h for h in remaining_header))

    def test_extract_delete_matched_complement(self):
        pattern = "PSU"
        extracted = list(extract_matched_columns(ALL_LINES, pattern))
        deleted = list(delete_matched_columns(ALL_LINES, pattern))
        e_cols = len(extracted[3].split(DELIM)) if extracted[3] else 0
        d_cols = len(deleted[3].split(DELIM))
        self.assertEqual(e_cols + d_cols, TOTAL_COLS)

    def test_pre_header_comments_pass_through(self):
        result = list(delete_matched_columns(ALL_LINES, "Comment"))
        self.assertEqual(result[0], ALL_LINES[0])
        self.assertEqual(result[2], ALL_LINES[2])

    def test_empty_input(self):
        self.assertEqual(list(delete_matched_columns([], "Station")), [])


if __name__ == "__main__":
    unittest.main()
