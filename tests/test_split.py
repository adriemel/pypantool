"""Tests for core/split.py."""

from pathlib import Path

import pytest

from core.split import split_by_columns, split_by_lines, split_by_size

FIXTURE = Path(__file__).parent / "fixtures" / "test_data.txt"


def _load() -> list[str]:
    with open(FIXTURE, encoding="UTF-8") as fh:
        return [line.rstrip("\n") for line in fh]


ALL_LINES = _load()


def _chunks(pairs) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for idx, line in pairs:
        out.setdefault(idx, []).append(line)
    return out


class TestSplitByLines:
    def test_even_split(self):
        chunks = _chunks(split_by_lines(["a", "b", "c", "d"], lines_per_file=2))
        assert chunks == {1: ["a", "b"], 2: ["c", "d"]}

    def test_remainder_chunk(self):
        chunks = _chunks(split_by_lines(["a", "b", "c"], lines_per_file=2))
        assert chunks == {1: ["a", "b"], 2: ["c"]}

    def test_header_repeated(self):
        chunks = _chunks(split_by_lines(
            ["H", "a", "b", "c"], lines_per_file=2, header_lines=1,
        ))
        assert chunks == {1: ["H", "a", "b"], 2: ["H", "c"]}

    def test_indices_monotonic(self):
        indices = [i for i, _ in split_by_lines(ALL_LINES, lines_per_file=10)]
        assert indices == sorted(indices)

    def test_fixture_all_lines_present(self):
        chunks = _chunks(split_by_lines(ALL_LINES, lines_per_file=10))
        merged = [line for idx in sorted(chunks) for line in chunks[idx]]
        assert merged == ALL_LINES

    def test_single_chunk_when_short(self):
        chunks = _chunks(split_by_lines(["a", "b"], lines_per_file=100))
        assert chunks == {1: ["a", "b"]}

    def test_invalid_lines_per_file(self):
        with pytest.raises(ValueError):
            list(split_by_lines(["a"], lines_per_file=0))

    def test_negative_header_lines(self):
        with pytest.raises(ValueError):
            list(split_by_lines(["a"], lines_per_file=1, header_lines=-1))

    def test_empty_input(self):
        assert list(split_by_lines([], lines_per_file=5)) == []


class TestSplitBySize:
    def test_line_cap(self):
        chunks = _chunks(split_by_size(["a", "b", "c"], max_lines=2))
        assert chunks == {1: ["a", "b"], 2: ["c"]}

    def test_size_cap(self):
        # Each line is 5 chars + newline = 6; cap of 12 fits two lines.
        chunks = _chunks(split_by_size(["aaaaa", "bbbbb", "ccccc"], max_bytes=12))
        assert chunks == {1: ["aaaaa", "bbbbb"], 2: ["ccccc"]}

    def test_header_repeated(self):
        chunks = _chunks(split_by_size(
            ["H", "a", "b", "c"], max_lines=2, header_lines=1,
        ))
        assert chunks == {1: ["H", "a", "b"], 2: ["H", "c"]}

    def test_defaults_single_chunk(self):
        chunks = _chunks(split_by_size(ALL_LINES))
        assert list(chunks) == [1]

    def test_invalid_caps(self):
        with pytest.raises(ValueError):
            list(split_by_size(["a"], max_bytes=0))


class TestSplitByColumns:
    def test_one_column_per_file(self):
        chunks = _chunks(split_by_columns(["a\tb\tc", "1\t2\t3"], columns_per_file=1))
        assert chunks == {1: ["a", "1"], 2: ["b", "2"], 3: ["c", "3"]}

    def test_two_columns_per_file(self):
        chunks = _chunks(split_by_columns(["a\tb\tc", "1\t2\t3"], columns_per_file=2))
        assert chunks == {1: ["a\tb", "1\t2"], 2: ["c", "3"]}

    def test_fixed_columns_repeated(self):
        chunks = _chunks(split_by_columns(
            ["id\ta\tb", "x\t1\t2"], columns_per_file=1, fixed_spec="1",
        ))
        assert chunks == {1: ["id\ta", "x\t1"], 2: ["id\tb", "x\t2"]}

    def test_comment_lines_pass_through_to_all_chunks(self):
        chunks = _chunks(split_by_columns(
            ["a\tb", "// note", "1\t2"], columns_per_file=1,
        ))
        assert chunks[1] == ["a", "// note", "1"]
        assert chunks[2] == ["b", "// note", "2"]

    def test_fixture_chunk_count(self):
        # Fixture data lines have 11 columns; first line is a comment without
        # tabs, so the whole-line pass-through applies to it.
        data_lines = [l for l in ALL_LINES if "\t" in l]
        chunks = _chunks(split_by_columns(data_lines, columns_per_file=3))
        assert len(chunks) == 4  # ceil(11 / 3)

    def test_no_data_columns_raises(self):
        with pytest.raises(ValueError, match="No data columns"):
            list(split_by_columns(["a\tb", "1\t2"], columns_per_file=1, fixed_spec="1-2"))

    def test_invalid_columns_per_file(self):
        with pytest.raises(ValueError):
            list(split_by_columns(["a\tb"], columns_per_file=0))

    def test_empty_input(self):
        assert list(split_by_columns([], columns_per_file=1)) == []
