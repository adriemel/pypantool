"""Tests for core/naming.py — run with: python3 -m pytest tests/"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.naming import output_problem, resolve_output_name, unique_path

FIXTURE = Path(__file__).parent / "fixtures" / "test_data.txt"


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


class TestOutputProblem(unittest.TestCase):

    def test_distinct_outputs_ok(self):
        ins = [Path("a.txt"), Path("b.txt")]
        outs = [Path("a_out.txt"), Path("b_out.txt")]
        self.assertIsNone(output_problem(ins, outs))

    def test_output_equals_input(self):
        # Pattern "%N%E" maps the fixture onto itself.
        msg = output_problem([FIXTURE], [FIXTURE.parent / "test_data.txt"])
        self.assertIn("overwrite an input", msg)

    def test_output_is_other_input(self):
        ins = [Path("a.txt"), Path("a_out.txt")]
        outs = [Path("a_out.txt"), Path("a_out_out.txt")]
        self.assertIn("overwrite an input", output_problem(ins, outs))

    def test_shared_output_name(self):
        # Pattern without %N sends every file to the same output.
        ins = [Path("a.txt"), Path("b.txt")]
        outs = [Path("out.txt"), Path("out.txt")]
        self.assertIn("same output", output_problem(ins, outs))

    def test_relative_and_absolute_same_file(self):
        rel = Path("x.txt")
        self.assertIsNotNone(output_problem([rel], [rel.absolute()]))


if __name__ == "__main__":
    unittest.main()
