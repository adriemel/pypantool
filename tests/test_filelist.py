"""Tests for core/filelist.py — run with: python3 -m pytest tests/"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.filelist import emit_filelist

FIXTURE_DIR = Path(__file__).parent / "fixtures"
FIXTURE_A = FIXTURE_DIR / "test_data.txt"
FIXTURE_B = FIXTURE_DIR / "test_data_supplement.txt"


class TestEmitFilelist(unittest.TestCase):

    def test_header_is_first_row(self):
        result = list(emit_filelist([FIXTURE_A]))
        self.assertTrue(result[0].startswith("Name\t"))
        self.assertIn("Path", result[0])
        self.assertIn("Size (bytes)", result[0])
        self.assertIn("Modified", result[0])

    def test_one_data_row_per_file(self):
        result = list(emit_filelist([FIXTURE_A, FIXTURE_B]))
        # 1 header + 2 data rows
        self.assertEqual(len(result), 3)

    def test_empty_files_yields_header_only(self):
        result = list(emit_filelist([]))
        self.assertEqual(len(result), 1)
        self.assertIn("Name", result[0])

    def test_data_row_contains_filename(self):
        result = list(emit_filelist([FIXTURE_A]))
        self.assertIn("test_data.txt", result[1])

    def test_data_row_contains_parent_dir(self):
        result = list(emit_filelist([FIXTURE_A]))
        self.assertIn(str(FIXTURE_A.parent), result[1])

    def test_data_row_contains_correct_size(self):
        expected_size = str(FIXTURE_A.stat().st_size)
        result = list(emit_filelist([FIXTURE_A]))
        self.assertIn(expected_size, result[1])

    def test_data_row_contains_timestamp(self):
        result = list(emit_filelist([FIXTURE_A]))
        # Timestamp format: YYYY-MM-DD HH:MM:SS
        parts = result[1].split("\t")
        self.assertEqual(len(parts), 4)
        timestamp = parts[3]
        self.assertRegex(timestamp, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

    def test_row_order_matches_input_order(self):
        result = list(emit_filelist([FIXTURE_A, FIXTURE_B]))
        self.assertIn("test_data.txt", result[1])
        self.assertIn("test_data_supplement.txt", result[2])

    def test_custom_delimiter(self):
        result = list(emit_filelist([FIXTURE_A], delimiter=","))
        self.assertTrue(result[0].startswith("Name,"))
        parts = result[1].split(",")
        self.assertGreaterEqual(len(parts), 4)

    def test_nonexistent_file_emits_na(self):
        ghost = Path("/nonexistent/ghost_file.txt")
        result = list(emit_filelist([ghost]))
        self.assertIn("N/A", result[1])


if __name__ == "__main__":
    unittest.main()
