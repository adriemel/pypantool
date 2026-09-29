"""Tests for core/naming.py — run with: python3 -m pytest tests/"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.naming import resolve_output_name, unique_path


class TestResolveOutputName(unittest.TestCase):

    def test_tokens(self):
        name = resolve_output_name("%N_%a%E", Path("data.tab"), 3)
        self.assertEqual(name, "data_3.tab")


class TestUniquePath(unittest.TestCase):

    def test_free_name_used_as_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self.assertEqual(unique_path(d, "Concatenate_out", ".tab"), d / "Concatenate_out.tab")

    def test_taken_names_are_numbered(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "Concatenate_out.tab").touch()
            (d / "Concatenate_out_2.tab").touch()
            self.assertEqual(unique_path(d, "Concatenate_out", ".tab"), d / "Concatenate_out_3.tab")


if __name__ == "__main__":
    unittest.main()
