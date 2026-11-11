"""Tests for the shared header rule and the tools that rely on it."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.addcol import add_column
from core.columns import (
    delete_columns,
    delete_matched_columns,
    extract_columns,
    extract_matched_columns,
    parse_column_spec,
)
from core.compress import compress_file_gzip, decompress_file
from core.header import header_finder
from core.recalc import recalculate_columns
from core.rename import preview_renames, rename_problem
from core.split import split_by_columns
from core.timeseries import extract_interval_lines

FIXTURES = Path(__file__).parent / "fixtures"
PANGAEA = (FIXTURES / "test_pangaea_header.txt").read_text(encoding="utf-8").splitlines()
PLAIN = (FIXTURES / "test_data.txt").read_text(encoding="utf-8").splitlines()
BLOCK = PANGAEA[:5]          # /* ... */ metadata block
COMMENT = PANGAEA[8]         # mid-file comment line containing a tab


def _header_index(lines: list[str], **kwargs) -> int:
    is_header = header_finder(**kwargs)
    return next(i for i, line in enumerate(lines, start=1) if is_header(i, line))


class TestHeaderFinder:
    def test_skips_pangaea_block(self):
        assert _header_index(PANGAEA) == 6

    def test_skips_leading_comments(self):
        assert _header_index(PLAIN) == 4

    def test_header_line_setting(self):
        assert _header_index(PLAIN, header_line=5) == 5

    def test_invalid_header_line(self):
        with pytest.raises(ValueError):
            header_finder(header_line=0)


class TestColumnSpecValidation:
    def test_zero_rejected(self):
        with pytest.raises(ValueError, match="1 or greater"):
            parse_column_spec("0", 5)

    def test_beyond_last_column_rejected(self):
        with pytest.raises(ValueError, match="does not exist"):
            parse_column_spec("9", 5)


class TestColumnsWithMetadataBlock:
    def test_extract_end_uses_header_width(self):
        result = list(extract_columns(PANGAEA, "3-end"))
        assert result[:5] == BLOCK
        assert result[5] == "Depth water [m]\tTemp [°C]\tSal"
        assert result[6] == "10\t-1.820\t34.12"

    def test_comment_with_delimiter_untouched(self):
        assert list(extract_columns(PANGAEA, "1"))[8] == COMMENT

    def test_short_row_padded_not_shifted(self):
        assert list(extract_columns(PANGAEA, "1,5"))[9] == "PS001\t"

    def test_delete_columns(self):
        result = list(delete_columns(PANGAEA, "2"))
        assert result[:5] == BLOCK
        assert result[5] == "Event\tDepth water [m]\tTemp [°C]\tSal"

    def test_extract_matched(self):
        result = list(extract_matched_columns(PANGAEA, "Temp"))
        assert result[:5] == BLOCK
        assert result[5:8] == ["Temp [°C]", "-1.820", "-1.80"]

    def test_delete_matched_no_match_raises(self):
        with pytest.raises(ValueError, match="No column header matches"):
            list(delete_matched_columns(PANGAEA, "NOTEXIST"))


class TestSplitByColumnsWithMetadataBlock:
    def test_chunks_use_header_width(self):
        pairs = list(split_by_columns(PANGAEA, 2, fixed_spec="1-2"))
        assert {idx for idx, _ in pairs} == {1, 2}
        chunk2 = [line for idx, line in pairs if idx == 2]
        assert chunk2[:5] == BLOCK
        assert chunk2[5] == "Event\tDate/Time\tSal"

    def test_no_header_raises(self):
        with pytest.raises(ValueError, match="No header line"):
            list(split_by_columns(["a", "b"], 1))


class TestRecalcPrecision:
    def test_trailing_zeros_and_text_kept(self):
        result = list(recalculate_columns(PANGAEA, "4", factor=1, offset=0))
        assert result[:6] == PANGAEA[:6]
        assert result[6].split("\t")[3] == "-1.820"
        assert result[10].split("\t")[3] == "n.d."

    def test_exact_decimal_arithmetic(self):
        result = list(recalculate_columns(PANGAEA, "4", factor=3, offset=0.1))
        assert result[6].split("\t")[3] == "-5.360"

    def test_long_integer_and_non_plain_numbers(self):
        line = "123456789012345678\t1_000\tnan\t1,5"
        assert list(recalculate_columns([line], "1-end", 1, 0)) == [line]


class TestTimeseriesWithMetadataBlock:
    def test_header_found_after_block(self):
        data = [line for line in PANGAEA if line != COMMENT]
        result = list(extract_interval_lines(data))
        assert result[:6] == data[:6]
        assert [r.split("\t")[1] for r in result[6:]] == [
            "2024-01-15T08:00", "2024-01-15T08:20", "2024-01-15T08:40",
        ]

    def test_mixed_utc_offsets_raise_clearly(self):
        lines = ["Date/Time\tT", "2024-01-01T00:00\t1",
                 "2024-01-01T00:20Z\t1", "2024-01-01T00:40\t1"]
        with pytest.raises(ValueError, match="UTC offset"):
            list(extract_interval_lines(lines))


class TestAddColumnWithMetadataBlock:
    def test_preamble_and_comments_untouched(self):
        result = list(add_column(PANGAEA, add_ordinal=True))
        assert result[:5] == BLOCK
        assert result[5].startswith("No\tEvent")
        assert result[8] == COMMENT
        assert result[10].startswith("4\t")


class TestRenameProblem:
    def test_ok(self, tmp_path):
        (tmp_path / "a.txt").write_text("x")
        assert rename_problem(preview_renames([tmp_path / "a.txt"], prefix="p_")) is None

    def test_collision(self, tmp_path):
        paths = [tmp_path / "a1.txt", tmp_path / "a2.txt"]
        pairs = preview_renames(paths, search="1", replace="2")
        assert "Several files" in rename_problem(pairs)

    def test_existing_target(self, tmp_path):
        (tmp_path / "b.txt").write_text("x")
        pairs = preview_renames([tmp_path / "a.txt"], search="a", replace="b")
        assert "already exists" in rename_problem(pairs)

    def test_empty_name(self, tmp_path):
        pairs = preview_renames([tmp_path / "a.txt"], search="a.txt")
        assert "empty name" in rename_problem(pairs)


class TestDecompressNeverOverwrites:
    def test_existing_target_refused(self, tmp_path):
        src = tmp_path / "data.tab"
        src.write_text("original")
        archive = compress_file_gzip(src)
        with pytest.raises(FileExistsError):
            decompress_file(archive)
        assert src.read_text() == "original"
