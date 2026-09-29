"""Tests for core/concat.py — run with: python3 -m pytest tests/"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.concat import concat_by_columns, concat_by_lines

FIXTURE_A = Path(__file__).parent / "fixtures" / "test_data.txt"
FIXTURE_B = Path(__file__).parent / "fixtures" / "test_data_supplement.txt"

# test_data.txt:        35 lines (3 comments + 1 header + data + 1 empty + 1 comment)
# test_data_supplement: 8  lines (1 comment + 1 header + 6 data)
LINES_A = 35
LINES_B = 8


def _load(path: Path) -> list[str]:
    with open(path, encoding="UTF-8") as fh:
        return [line.rstrip("\n") for line in fh]


ALL_A = _load(FIXTURE_A)
ALL_B = _load(FIXTURE_B)


# ── concat_by_lines ──────────────────────────────────────────────────────────

class TestConcatByLines(unittest.TestCase):

    def _run(self, **kwargs) -> list[str]:
        inputs = [("test_data.txt", iter(ALL_A)), ("test_data_supplement.txt", iter(ALL_B))]
        return list(concat_by_lines(inputs, **kwargs))

    def test_no_options_appends_all_lines(self):
        result = self._run()
        self.assertEqual(len(result), LINES_A + LINES_B)

    def test_skip_1_header_from_second_file(self):
        # skip_header_lines=1 drops the first line of file B only.
        result = self._run(skip_header_lines=1)
        self.assertEqual(len(result), LINES_A + LINES_B - 1)

    def test_skip_2_headers_from_second_file(self):
        # skip 2 lines from file B (comment + column header).
        result = self._run(skip_header_lines=2)
        self.assertEqual(len(result), LINES_A + LINES_B - 2)

    def test_first_file_not_trimmed(self):
        # File A must appear in full regardless of skip_header_lines.
        result = self._run(skip_header_lines=3)
        # First line of file A is the first line of output.
        self.assertEqual(result[0], ALL_A[0])

    def test_filename_column_prefixes_data_lines(self):
        # Header = 4 lines of A (3 comments + column header).
        result = self._run(skip_header_lines=4, filename_column=True)
        self.assertEqual(len(result), LINES_A + LINES_B - 4)
        # Comments in the header pass through unchanged.
        self.assertEqual(result[:3], ALL_A[:3])
        self.assertEqual(result[3], "Filename\t" + ALL_A[3])
        self.assertEqual(result[4], "test_data\t" + ALL_A[4])
        self.assertEqual(result[LINES_A], "test_data_supplement\t" + ALL_B[4])

    def test_filename_column_leaves_comments_and_empty_lines(self):
        result = self._run(skip_header_lines=4, filename_column=True)
        for line in result:
            if line == "" or line.startswith("//"):
                continue
            first = line.split("\t", 1)[0]
            self.assertIn(first, ("Filename", "test_data", "test_data_supplement"))
        self.assertIn("", result)
        self.assertIn(ALL_A[24], result)  # mid-file comment, unprefixed

    def test_filename_column_without_header(self):
        # No header lines: the column header row is prefixed like data.
        result = self._run(filename_column=True)
        self.assertEqual(result[3], "test_data\t" + ALL_A[3])
        self.assertNotIn("Filename", [line.split("\t", 1)[0] for line in result])

    def test_filename_column_custom_delimiter(self):
        result = self._run(skip_header_lines=4, filename_column=True, delimiter=";")
        self.assertEqual(result[4], "test_data;" + ALL_A[4])

    def test_filename_column_with_skip_comments(self):
        result = self._run(skip_header_lines=4, filename_column=True, skip_comments=True)
        self.assertEqual(result[0], "Filename\t" + ALL_A[3])
        self.assertFalse(any(line.startswith("//") for line in result))

    def test_skip_empty_lines(self):
        base = self._run()
        base_empty = sum(1 for line in base if line == "")
        result = self._run(skip_empty=True)
        self.assertEqual(len(result), LINES_A + LINES_B - base_empty)
        self.assertNotIn("", result)

    def test_skip_comment_lines(self):
        base = self._run()
        base_comments = sum(1 for line in base if line.startswith("//"))
        result = self._run(skip_comments=True)
        self.assertEqual(len(result), LINES_A + LINES_B - base_comments)
        self.assertFalse(any(line.startswith("//") for line in result))

    def test_skip_empty_and_comments_combined(self):
        result = self._run(skip_empty=True, skip_comments=True)
        self.assertNotIn("", result)
        self.assertFalse(any(line.startswith("//") for line in result))

    def test_empty_comment_prefix_raises(self):
        with self.assertRaises(ValueError):
            inputs = [("a", iter(["x"]))]
            list(concat_by_lines(inputs, skip_comments=True, comment_prefix=""))

    def test_single_file_no_skip(self):
        inputs = [("test_data.txt", iter(ALL_A))]
        result = list(concat_by_lines(inputs))
        self.assertEqual(result, ALL_A)

    def test_empty_inputs(self):
        result = list(concat_by_lines([]))
        self.assertEqual(result, [])

    def test_order_preserved(self):
        # File A content must precede file B content in output.
        result = self._run(skip_header_lines=0)
        a_last = result.index(ALL_A[-1])
        b_first_idx = result.index(ALL_B[0])
        self.assertLess(a_last, b_first_idx)


# ── concat_by_columns ────────────────────────────────────────────────────────

class TestConcatByColumns(unittest.TestCase):

    def _pairs(self, *line_lists, names=None):
        if names is None:
            names = [f"file{i}.txt" for i in range(len(line_lists))]
        return [(n, iter(ll)) for n, ll in zip(names, line_lists)]

    def test_basic_zip(self):
        # Two files, same row count — join side by side.
        a = ["h1\th2", "1\t2", "3\t4"]
        b = ["h3\th4", "x\ty", "p\tq"]
        result = list(concat_by_columns(self._pairs(a, b)))
        self.assertEqual(result[0], "h1\th2\th3\th4")
        self.assertEqual(result[1], "1\t2\tx\ty")
        self.assertEqual(result[2], "3\t4\tp\tq")

    def test_row_count_mismatch_raises(self):
        # Fixture files have different row counts → ValueError.
        inputs = [
            ("test_data.txt", iter(ALL_A)),
            ("test_data_supplement.txt", iter(ALL_B)),
        ]
        with self.assertRaises(ValueError):
            list(concat_by_columns(inputs))

    def test_skip_header_lines(self):
        a = ["hdr", "1", "2", "3"]
        b = ["hdr", "a", "b", "c"]
        result = list(concat_by_columns(self._pairs(a, b), skip_header_lines=1))
        # Header "hdr" skipped from both; 3 data rows remain.
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "1\ta")

    def test_include_filename_row(self):
        a = ["1", "2"]
        b = ["x", "y"]
        result = list(concat_by_columns(
            self._pairs(a, b, names=["alpha.txt", "beta.txt"]),
            include_filename_row=True,
        ))
        self.assertEqual(result[0], "alpha.txt\tbeta.txt")
        self.assertEqual(result[1], "1\tx")
        self.assertEqual(result[2], "2\ty")

    def test_include_filename_row_and_skip_header(self):
        a = ["col_a", "1", "2"]
        b = ["col_b", "x", "y"]
        result = list(concat_by_columns(
            self._pairs(a, b, names=["f1.txt", "f2.txt"]),
            skip_header_lines=1,
            include_filename_row=True,
        ))
        # First row = filenames, then 2 data rows.
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "f1.txt\tf2.txt")
        self.assertEqual(result[1], "1\tx")

    def test_same_file_twice(self):
        # Concatenating a file with itself doubles the columns.
        inputs = [
            ("test_data.txt", iter(ALL_A)),
            ("test_data.txt", iter(ALL_A)),
        ]
        result = list(concat_by_columns(inputs))
        self.assertEqual(len(result), LINES_A)
        # Each output row = original row joined with itself.
        self.assertEqual(result[0], ALL_A[0] + "\t" + ALL_A[0])

    def test_custom_delimiter(self):
        a = ["a,b", "1,2"]
        b = ["c,d", "3,4"]
        result = list(concat_by_columns(self._pairs(a, b), delimiter=","))
        self.assertEqual(result[0], "a,b,c,d")
        self.assertEqual(result[1], "1,2,3,4")

    def test_empty_inputs(self):
        result = list(concat_by_columns([]))
        self.assertEqual(result, [])

    def test_single_file_passthrough(self):
        a = ["h", "1", "2"]
        result = list(concat_by_columns(self._pairs(a)))
        self.assertEqual(result, a)


if __name__ == "__main__":
    unittest.main()
