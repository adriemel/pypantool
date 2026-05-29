"""Tests for core/lines.py — run with: python3 -m unittest tests.test_lines"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.lines import (
    _build_line_predicate,
    delete_lines,
    delete_matched_lines,
    extract_lines,
    extract_matched_lines,
)

FIXTURE = Path(__file__).parent / "fixtures" / "test_data.txt"


def _load() -> list[str]:
    """Return fixture lines with trailing newlines stripped."""
    with open(FIXTURE, encoding="UTF-8") as fh:
        return [line.rstrip("\n") for line in fh]


ALL_LINES = _load()
# Fixture structure (35 lines total, verified):
#   1-3:   comment lines (//)
#   4:     header
#   5-10:  PS001 data (6 rows)
#   11-16: PS002 data (6 rows)
#   17:    empty line
#   18-23: PS003 data (6 rows)
#   24:    PS003 duplicate (500m, same as line 23)
#   25:    // End of station PS003 data
#   26-33: PS004 data (8 rows)
#   34:    PS002 duplicate (same as line 11)
#   35:    PS001 duplicate (same as line 5)
TOTAL = 35


class TestBuildLinePredicate(unittest.TestCase):
    def test_single_number(self):
        p = _build_line_predicate("5")
        self.assertTrue(p(5))
        self.assertFalse(p(4))
        self.assertFalse(p(6))

    def test_range(self):
        p = _build_line_predicate("3-5")
        self.assertFalse(p(2))
        self.assertTrue(p(3))
        self.assertTrue(p(4))
        self.assertTrue(p(5))
        self.assertFalse(p(6))

    def test_end_range(self):
        p = _build_line_predicate("33-end")
        self.assertFalse(p(32))
        self.assertTrue(p(33))
        self.assertTrue(p(35))
        self.assertTrue(p(999))

    def test_comma_list(self):
        p = _build_line_predicate("1,3,5")
        self.assertTrue(p(1))
        self.assertFalse(p(2))
        self.assertTrue(p(3))
        self.assertTrue(p(5))

    def test_mixed_spec(self):
        p = _build_line_predicate("1-3,5,10-end")
        self.assertTrue(p(1))
        self.assertTrue(p(3))
        self.assertFalse(p(4))
        self.assertTrue(p(5))
        self.assertFalse(p(9))
        self.assertTrue(p(10))
        self.assertTrue(p(100))

    def test_empty_spec_raises(self):
        with self.assertRaises(ValueError):
            _build_line_predicate("")

    def test_invalid_number_raises(self):
        with self.assertRaises(ValueError):
            _build_line_predicate("abc")

    def test_inverted_range_raises(self):
        with self.assertRaises(ValueError):
            _build_line_predicate("5-3")


class TestExtractLines(unittest.TestCase):
    def test_single_line(self):
        result = list(extract_lines(ALL_LINES, "4"))
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].startswith("Station\t"))

    def test_range(self):
        result = list(extract_lines(ALL_LINES, "1-3"))
        self.assertEqual(len(result), 3)
        self.assertTrue(all(line.startswith("//") for line in result))

    def test_end_range(self):
        result = list(extract_lines(ALL_LINES, "34-end"))
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0].startswith("PS002"))
        self.assertTrue(result[1].startswith("PS001"))

    def test_comma_list(self):
        result = list(extract_lines(ALL_LINES, "1,4"))
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0].startswith("//"))
        self.assertTrue(result[1].startswith("Station"))

    def test_empty_line_extracted(self):
        result = list(extract_lines(ALL_LINES, "17"))
        self.assertEqual(result, [""])

    def test_no_match_returns_empty(self):
        result = list(extract_lines(ALL_LINES, "999"))
        self.assertEqual(result, [])

    def test_adjacent_duplicates_both_extracted(self):
        result = list(extract_lines(ALL_LINES, "23-24"))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], result[1])


class TestDeleteLines(unittest.TestCase):
    def test_delete_header_comments(self):
        result = list(delete_lines(ALL_LINES, "1-3"))
        self.assertEqual(len(result), TOTAL - 3)
        self.assertFalse(result[0].startswith("//"))

    def test_delete_single(self):
        result = list(delete_lines(ALL_LINES, "17"))
        self.assertEqual(len(result), TOTAL - 1)
        # After removing empty line 17, what was line 18 is now at index 16.
        self.assertTrue(result[16].startswith("PS003"))

    def test_delete_end_range(self):
        result = list(delete_lines(ALL_LINES, "34-end"))
        self.assertEqual(len(result), 33)
        self.assertTrue(result[-1].startswith("PS004"))

    def test_delete_nothing_returns_all(self):
        result = list(delete_lines(ALL_LINES, "999"))
        self.assertEqual(result, ALL_LINES)

    def test_extract_and_delete_partition(self):
        spec = "1-3,17,25"
        extracted = list(extract_lines(ALL_LINES, spec))
        deleted = list(delete_lines(ALL_LINES, spec))
        self.assertEqual(len(extracted) + len(deleted), TOTAL)


class TestExtractMatchedLines(unittest.TestCase):
    def test_substring_match(self):
        result = list(extract_matched_lines(ALL_LINES, "PS001"))
        # 6 original rows (lines 5-10) + 1 duplicate (line 35) = 7
        self.assertEqual(len(result), 7)
        self.assertTrue(all("PS001" in line for line in result))

    def test_no_match_returns_empty(self):
        result = list(extract_matched_lines(ALL_LINES, "NOTEXIST"))
        self.assertEqual(result, [])

    def test_regex_match(self):
        result = list(extract_matched_lines(ALL_LINES, r"PS00[12]", is_regex=True))
        # PS001: 7, PS002: 7 (6 original + 1 duplicate each)
        self.assertEqual(len(result), 14)
        self.assertTrue(
            all(line.startswith("PS001") or line.startswith("PS002") for line in result)
        )

    def test_regex_line_start_anchor(self):
        # Comment lines 1, 2, 3, 25
        result = list(extract_matched_lines(ALL_LINES, r"^//", is_regex=True))
        self.assertEqual(len(result), 4)
        self.assertTrue(all(line.startswith("//") for line in result))

    def test_case_sensitive(self):
        result = list(extract_matched_lines(ALL_LINES, "ps001"))
        self.assertEqual(result, [])


class TestDeleteMatchedLines(unittest.TestCase):
    def test_delete_all_comment_lines(self):
        result = list(delete_matched_lines(ALL_LINES, "^//", is_regex=True))
        self.assertEqual(len(result), TOTAL - 4)
        self.assertFalse(any(line.startswith("//") for line in result))

    def test_delete_station(self):
        result = list(delete_matched_lines(ALL_LINES, "PS003"))
        # 6 unique rows + 1 adjacent duplicate + 1 mid-file comment ("// End of station PS003 data") = 8
        self.assertEqual(len(result), TOTAL - 8)
        self.assertFalse(any("PS003" in line for line in result))

    def test_extract_and_delete_matched_partition(self):
        pattern = "PS004"
        extracted = list(extract_matched_lines(ALL_LINES, pattern))
        deleted = list(delete_matched_lines(ALL_LINES, pattern))
        self.assertEqual(len(extracted) + len(deleted), TOTAL)

    def test_delete_nothing(self):
        result = list(delete_matched_lines(ALL_LINES, "NOTEXIST"))
        self.assertEqual(result, ALL_LINES)


if __name__ == "__main__":
    unittest.main()
