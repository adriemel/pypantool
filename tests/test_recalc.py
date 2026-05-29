"""Tests for core/recalc.py."""

import pytest

from core.recalc import recalculate_columns


def lines(*args):
    return list(args)


class TestRecalculateColumns:
    def test_multiply_single_column(self):
        result = list(recalculate_columns(
            lines("a\t2\tc", "d\t4\tf"),
            spec="2", factor=2.0, offset=0.0,
        ))
        assert result == ["a\t4\tc", "d\t8\tf"]

    def test_add_offset(self):
        result = list(recalculate_columns(
            lines("1\t10"),
            spec="2", factor=1.0, offset=5.0,
        ))
        assert result == ["1\t15"]

    def test_factor_and_offset(self):
        result = list(recalculate_columns(
            lines("1\t10"),
            spec="2", factor=2.0, offset=3.0,
        ))
        assert result == ["1\t23"]

    def test_multiple_columns(self):
        result = list(recalculate_columns(
            lines("1\t2\t3"),
            spec="1,3", factor=10.0, offset=0.0,
        ))
        assert result == ["10\t2\t30"]

    def test_column_range(self):
        result = list(recalculate_columns(
            lines("1\t2\t3\t4"),
            spec="2-3", factor=0.0, offset=0.0,
        ))
        assert result == ["1\t0\t0\t4"]

    def test_non_numeric_passed_through(self):
        result = list(recalculate_columns(
            lines("hdr\tval\tend", "a\t5\tb"),
            spec="2", factor=2.0, offset=0.0, header_lines=1,
        ))
        assert result == ["hdr\tval\tend", "a\t10\tb"]

    def test_header_lines_skipped(self):
        result = list(recalculate_columns(
            lines("Station\tDepth\tTemp", "A\t100\t3.5"),
            spec="2", factor=1.0, offset=1000.0, header_lines=1,
        ))
        assert result[0] == "Station\tDepth\tTemp"
        assert result[1] == "A\t1100\t3.5"

    def test_line_without_delimiter_passes_through(self):
        result = list(recalculate_columns(
            lines("// comment", "1\t2"),
            spec="2", factor=2.0, offset=0.0,
        ))
        assert result[0] == "// comment"
        assert result[1] == "1\t4"

    def test_empty_input(self):
        assert list(recalculate_columns([], spec="1", factor=2.0, offset=0.0)) == []

    def test_custom_delimiter(self):
        result = list(recalculate_columns(
            lines("a;2;c"),
            spec="2", factor=3.0, offset=0.0, delimiter=";",
        ))
        assert result == ["a;6;c"]

    def test_integer_result_no_decimal(self):
        result = list(recalculate_columns(
            lines("x\t5"),
            spec="2", factor=2.0, offset=0.0,
        ))
        # 5 * 2 = 10 — should not be "10.0"
        assert result == ["x\t10"]

    def test_floating_point_result(self):
        result = list(recalculate_columns(
            lines("x\t1"),
            spec="2", factor=0.5, offset=0.0,
        ))
        assert result == ["x\t0.5"]
