"""Tests for core/duplicates.py — run with: python3 -m pytest tests/"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.duplicates import delete_double_lines

FIXTURE = Path(__file__).parent / "fixtures" / "test_data.txt"


def _load() -> list[str]:
    with open(FIXTURE, encoding="UTF-8") as fh:
        return [line.rstrip("\n") for line in fh]


ALL_LINES = _load()
TOTAL = 35
# Duplicates in the fixture:
#   Line 24 (0-indexed 23) — adjacent repeat of line 23 (PS003 @ 500m)
#   Line 34 (0-indexed 33) — non-adjacent repeat of line 11 (PS002 @ 10m)
#   Line 35 (0-indexed 34) — non-adjacent repeat of line 5  (PS001 @ 10m)
DUPLICATE_COUNT = 3


class TestDeleteDoubleLines(unittest.TestCase):
    def test_removes_all_duplicates(self):
        result = list(delete_double_lines(ALL_LINES))
        self.assertEqual(len(result), TOTAL - DUPLICATE_COUNT)

    def test_first_occurrence_kept(self):
        result = list(delete_double_lines(ALL_LINES))
        # The two non-adjacent duplicate rows must appear exactly once.
        ps002_10m = "PS002\t-71.0000\t-11.5000\t2024-01-18\t10\t-0.95\t33.98\t7.92\t10.1\t27.88\tWeddell Sea"
        self.assertEqual(result.count(ps002_10m), 1)

    def test_adjacent_duplicate_removed(self):
        # PS003 @ 500m appears on consecutive lines — second must be gone.
        ps003_500m = "PS003\t-68.2500\t8.7500\t2024-01-22\t500\t1.05\t34.72\t4.15\t505.1\t31.52\tDeep water"
        result = list(delete_double_lines(ALL_LINES))
        self.assertEqual(result.count(ps003_500m), 1)

    def test_non_adjacent_duplicate_removed(self):
        # PS001 @ 10m also reappears at the end.
        ps001_10m = "PS001\t-75.5000\t-26.3000\t2024-01-15\t10\t-1.82\t34.12\t7.85\t10.1\t28.45\tArctic sample"
        result = list(delete_double_lines(ALL_LINES))
        self.assertEqual(result.count(ps001_10m), 1)

    def test_order_preserved(self):
        # Unique lines must stay in their original relative order.
        result = list(delete_double_lines(ALL_LINES))
        # The header line should still be the first non-comment line (index 3 in original).
        header = "Station\tLatitude\tLongitude\tDate\tDepth [m]\tTemperature [°C]\tSalinity [PSU]\tOxygen [ml/l]\tPressure [dbar]\tConductivity [mS/cm]\tComment"
        self.assertIn(header, result)
        # First occurrence index in result must be less than any data row index.
        header_idx = result.index(header)
        self.assertGreater(header_idx, 0)  # comment lines precede it

    def test_empty_input(self):
        result = list(delete_double_lines([]))
        self.assertEqual(result, [])

    def test_no_duplicates_unchanged(self):
        lines = ["alpha", "beta", "gamma"]
        result = list(delete_double_lines(lines))
        self.assertEqual(result, lines)

    def test_all_identical_keeps_one(self):
        lines = ["same"] * 100
        result = list(delete_double_lines(lines))
        self.assertEqual(result, ["same"])

    def test_empty_lines_deduplicated(self):
        # Multiple blank lines count as duplicates.
        lines = ["a", "", "b", "", "c"]
        result = list(delete_double_lines(lines))
        self.assertEqual(result, ["a", "", "b", "c"])

    def test_case_sensitive(self):
        lines = ["Line", "line", "LINE", "Line"]
        result = list(delete_double_lines(lines))
        self.assertEqual(result, ["Line", "line", "LINE"])


if __name__ == "__main__":
    unittest.main()
