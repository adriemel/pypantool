"""Tests for core/search_replace.py — run with: python3 -m pytest tests/"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.search_replace import (
    load_replacements,
    search_one_string,
    search_replace_many,
    search_replace_one,
)

FIXTURE = Path(__file__).parent / "fixtures" / "test_data.txt"


def _load() -> list[str]:
    with open(FIXTURE, encoding="UTF-8") as fh:
        return [line.rstrip("\n") for line in fh]


ALL_LINES = _load()
TOTAL = 35

# PS001 appears 6 times originally + 1 duplicate at the end = 7 data lines,
# plus 0 in comments/header.  Station column value "PS001" appears on those 7 lines.
PS001_COUNT = 7


# ── search_replace_one ───────────────────────────────────────────────────────

class TestSearchReplaceOne(unittest.TestCase):

    def test_replaces_all_occurrences_in_all_lines(self):
        result = list(search_replace_one(ALL_LINES, "PS001", "STATION_A"))
        replaced = [l for l in result if "STATION_A" in l]
        original = [l for l in result if "PS001" in l]
        self.assertEqual(len(replaced), PS001_COUNT)
        self.assertEqual(len(original), 0)

    def test_total_line_count_unchanged(self):
        result = list(search_replace_one(ALL_LINES, "PS001", "X"))
        self.assertEqual(len(result), TOTAL)

    def test_multiple_occurrences_within_one_line(self):
        lines = ["aXbXcX", "no match"]
        result = list(search_replace_one(lines, "X", "Y"))
        self.assertEqual(result[0], "aYbYcY")
        self.assertEqual(result[1], "no match")

    def test_no_match_lines_unchanged(self):
        result = list(search_replace_one(ALL_LINES, "NOTPRESENT", "X"))
        self.assertEqual(result, ALL_LINES)

    def test_replace_with_empty_string(self):
        # Replacing with "" is valid — effectively deletes the substring.
        result = list(search_replace_one(["hello world"], "world", ""))
        self.assertEqual(result, ["hello "])

    def test_empty_search_raises(self):
        with self.assertRaises(ValueError):
            list(search_replace_one(["line"], "", "x"))

    def test_empty_input(self):
        result = list(search_replace_one([], "a", "b"))
        self.assertEqual(result, [])

    def test_replaces_special_chars(self):
        # Header contains "[°C]" — should be replaceable.
        result = list(search_replace_one(ALL_LINES, "[°C]", "(degC)"))
        header_lines = [l for l in result if "(degC)" in l]
        self.assertGreater(len(header_lines), 0)
        self.assertFalse(any("[°C]" in l for l in result))

    def test_replace_tab_delimiter(self):
        lines = ["a\tb\tc"]
        result = list(search_replace_one(lines, "\t", ","))
        self.assertEqual(result, ["a,b,c"])


# ── search_replace_many ──────────────────────────────────────────────────────

class TestSearchReplaceMany(unittest.TestCase):

    def test_applies_all_pairs(self):
        replacements = [("PS001", "ALPHA"), ("PS002", "BETA")]
        result = list(search_replace_many(ALL_LINES, replacements))
        self.assertFalse(any("PS001" in l for l in result))
        self.assertFalse(any("PS002" in l for l in result))
        self.assertTrue(any("ALPHA" in l for l in result))
        self.assertTrue(any("BETA" in l for l in result))

    def test_pairs_applied_in_order(self):
        # Second replacement acts on output of first.
        lines = ["foo"]
        replacements = [("foo", "bar"), ("bar", "baz")]
        result = list(search_replace_many(lines, replacements))
        self.assertEqual(result, ["baz"])

    def test_empty_replacements_list_passthrough(self):
        result = list(search_replace_many(ALL_LINES, []))
        self.assertEqual(result, ALL_LINES)

    def test_empty_search_pair_skipped(self):
        # A pair with empty search string must be silently ignored.
        lines = ["hello"]
        result = list(search_replace_many(lines, [("", "X"), ("hello", "world")]))
        self.assertEqual(result, ["world"])

    def test_total_line_count_unchanged(self):
        replacements = [("PS003", "C"), ("PS004", "D")]
        result = list(search_replace_many(ALL_LINES, replacements))
        self.assertEqual(len(result), TOTAL)

    def test_empty_input(self):
        result = list(search_replace_many([], [("a", "b")]))
        self.assertEqual(result, [])


# ── load_replacements ────────────────────────────────────────────────────────

class TestLoadReplacements(unittest.TestCase):

    def test_basic_tab_delimited(self):
        lines = ["PS001\tSTATION_A", "PS002\tSTATION_B"]
        result = load_replacements(lines)
        self.assertEqual(result, [("PS001", "STATION_A"), ("PS002", "STATION_B")])

    def test_skips_blank_lines(self):
        lines = ["a\tb", "", "c\td"]
        result = load_replacements(lines)
        self.assertEqual(result, [("a", "b"), ("c", "d")])

    def test_skips_lines_without_delimiter(self):
        lines = ["valid\treplacement", "no_delimiter_here", "also\tok"]
        result = load_replacements(lines)
        self.assertEqual(result, [("valid", "replacement"), ("also", "ok")])

    def test_only_splits_on_first_delimiter(self):
        # Replace value may itself contain the delimiter.
        lines = ["search\treplace\twith\ttabs"]
        result = load_replacements(lines)
        self.assertEqual(result, [("search", "replace\twith\ttabs")])

    def test_custom_delimiter(self):
        lines = ["foo;bar", "baz;qux"]
        result = load_replacements(lines, delimiter=";")
        self.assertEqual(result, [("foo", "bar"), ("baz", "qux")])

    def test_empty_input(self):
        result = load_replacements([])
        self.assertEqual(result, [])

    def test_replace_value_can_be_empty(self):
        # "word\t" — replace with empty string is valid.
        lines = ["remove\t"]
        result = load_replacements(lines)
        self.assertEqual(result, [("remove", "")])


# ── search_one_string ─────────────────────────────────────────────────────────

class TestSearchOneString(unittest.TestCase):

    def test_header_row_first(self):
        result = list(search_one_string([("f.txt", ALL_LINES)], "PS001"))
        self.assertEqual(result[0], "Filename\tLine\tString")

    def test_reports_all_matches_with_line_numbers(self):
        result = list(search_one_string([("f.txt", ALL_LINES)], "PS001"))
        self.assertEqual(len(result), 1 + PS001_COUNT)
        for row in result[1:]:
            name, lineno, line = row.split("\t", 2)
            self.assertEqual(name, "f.txt")
            self.assertEqual(ALL_LINES[int(lineno) - 1], line)

    def test_multiple_files(self):
        result = list(search_one_string(
            [("a.txt", ["x", "hit"]), ("b.txt", ["hit", "y"])], "hit",
        ))
        self.assertEqual(result[1], "a.txt\t2\thit")
        self.assertEqual(result[2], "b.txt\t1\thit")

    def test_start_line_window(self):
        result = list(search_one_string(
            [("f", ["hit", "hit", "hit", "hit"])], "hit",
            start_line=2, num_lines=2,
        ))
        self.assertEqual(len(result), 3)  # header + lines 2 and 3
        self.assertEqual(result[1], "f\t2\thit")
        self.assertEqual(result[2], "f\t3\thit")

    def test_no_match_yields_header_only(self):
        result = list(search_one_string([("f", ["a", "b"])], "zzz"))
        self.assertEqual(result, ["Filename\tLine\tString"])

    def test_empty_search_raises(self):
        with self.assertRaises(ValueError):
            list(search_one_string([("f", ["a"])], ""))

    def test_invalid_start_line_raises(self):
        with self.assertRaises(ValueError):
            list(search_one_string([("f", ["a"])], "a", start_line=0))


if __name__ == "__main__":
    unittest.main()
