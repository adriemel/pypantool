"""Tests for core/comments.py — run with: python3 -m pytest tests/"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.comments import delete_comments

FIXTURE = Path(__file__).parent / "fixtures" / "test_data.txt"


def _load() -> list[str]:
    with open(FIXTURE, encoding="UTF-8") as fh:
        return [line.rstrip("\n") for line in fh]


ALL_LINES = _load()
# Comment lines in the fixture (1-based):
#   1:  // This is a comment line...
#   2:  // Data source: Test fixture...
#   3:  // Generated for feature validation
#   25: // End of station PS003 data
TOTAL = 35
COMMENT_COUNT = 4  # lines 1, 2, 3, 25


class TestDeleteComments(unittest.TestCase):
    def test_removes_default_prefix(self):
        result = list(delete_comments(ALL_LINES))
        self.assertEqual(len(result), TOTAL - COMMENT_COUNT)
        self.assertFalse(any(line.startswith("//") for line in result))

    def test_non_comment_lines_unchanged(self):
        result = list(delete_comments(ALL_LINES))
        # Header must still be present and intact.
        self.assertTrue(any(line.startswith("Station\t") for line in result))

    def test_empty_lines_preserved(self):
        # Line 17 is an empty line — it must survive comment removal.
        result = list(delete_comments(ALL_LINES))
        self.assertIn("", result)

    def test_custom_prefix(self):
        # Only lines starting with "PS001" should be removed.
        result = list(delete_comments(ALL_LINES, prefix="PS001"))
        # 6 original PS001 rows + 1 duplicate at end = 7 removed.
        self.assertEqual(len(result), TOTAL - 7)
        self.assertFalse(any(line.startswith("PS001") for line in result))

    def test_empty_input(self):
        result = list(delete_comments([], prefix="//"))
        self.assertEqual(result, [])

    def test_no_comments_returns_all(self):
        lines = ["hello", "world", "no comments here"]
        result = list(delete_comments(lines))
        self.assertEqual(result, lines)

    def test_all_comments_returns_empty(self):
        lines = ["// a", "// b", "// c"]
        result = list(delete_comments(lines))
        self.assertEqual(result, [])

    def test_empty_prefix_raises(self):
        with self.assertRaises(ValueError):
            list(delete_comments(ALL_LINES, prefix=""))

    def test_line_containing_prefix_but_not_starting(self):
        # A line that has "//" in the middle must NOT be removed.
        lines = ["value // comment", "// actual comment", "plain"]
        result = list(delete_comments(lines))
        self.assertEqual(result, ["value // comment", "plain"])


if __name__ == "__main__":
    unittest.main()
