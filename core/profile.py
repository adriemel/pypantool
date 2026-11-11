"""File statistics: one streaming pass that describes a tabular text file.

``profile_lines`` consumes the file and returns a :class:`TableProfile`;
``summary_rows`` / ``column_rows`` turn it into display text (used by the
statistics window) and ``format_profile`` into a tab-delimited report.

Unlike the other tools the input lines must keep their line endings and be
decoded with ``errors="surrogateescape"`` and ``newline=""``, so that line
endings, a byte-order mark and invalid bytes can be reported instead of
aborting the scan.  Memory use is proportional to the number of columns:
per column only counters, a few example values and at most
``DISTINCT_CAP`` value hashes are kept.
"""

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime

from core.header import header_finder, is_comment
from core.recalc import PLAIN_NUMBER

DISTINCT_CAP = 1000   # distinct values are counted exactly up to this number
EXAMPLES = 5          # example values / line numbers kept per finding

# Text that stands for "no value" (compared case-insensitively).
TEXT_MARKERS = frozenset({
    "na", "n/a", "n.a.", "nan", "nd", "n.d.", "null", "none", "missing",
    "#n/a", "#nv", "#value!", "#div/0!", "#ref!", "-", "--", "?", "inf", "-inf",
})
# Numeric fill values; counted as markers and left out of min/max.
NUMERIC_MARKERS = frozenset({
    "-999", "-9999", "-99999", "-999.0", "-9999.0", "-999.9", "-9999.9",
    "-999.99", "-9999.99",
})

_INVALID_BYTE = re.compile("[\udc80-\udcff]")


@dataclass(slots=True)
class ColumnProfile:
    """Statistics of one column (counts refer to data rows only)."""

    number: int                      # 1-based column number
    name: str
    is_datetime: bool = False
    filled: int = 0
    empty: int = 0
    numeric: int = 0
    padded: int = 0                  # cells with leading/trailing whitespace
    min_value: float | None = None
    max_value: float | None = None
    min_text: str = ""
    max_text: str = ""
    min_decimals: int | None = None
    max_decimals: int | None = None
    markers: dict[str, int] = field(default_factory=dict)
    other: int = 0                   # non-numeric, non-marker cells
    other_examples: dict[str, int] = field(default_factory=dict)  # value -> first line
    distinct: int | None = 0         # None = more than DISTINCT_CAP
    first_time: str = ""
    last_time: str = ""
    time_repeats: int = 0            # same timestamp as the line before
    time_backwards: int = 0          # earlier than the line before
    time_backwards_line: int = 0
    time_mixed_offsets: int = 0
    _seen: set[int] | None = field(default_factory=set, repr=False)
    _prev_time: datetime | None = field(default=None, repr=False)

    @property
    def kind(self) -> str:
        """``date/time``, ``numeric``, ``text``, ``mixed`` or ``empty``."""
        if self.is_datetime:
            return "date/time"
        if self.numeric and self.other:
            return "mixed"
        if self.numeric:
            return "numeric"
        if self.other:
            return "text"
        return "empty"

    def add(self, cell: str, lineno: int) -> None:
        text = cell.strip()
        if len(text) != len(cell):
            self.padded += 1
        if not text:
            self.empty += 1
            return
        self.filled += 1

        seen = self._seen
        if seen is not None:
            seen.add(hash(text))
            if len(seen) > DISTINCT_CAP:
                self._seen = None
                self.distinct = None
            else:
                self.distinct = len(seen)

        if self.is_datetime:
            self._add_time(text, lineno)
        elif PLAIN_NUMBER.fullmatch(text):
            if text in NUMERIC_MARKERS:
                self.markers[text] = self.markers.get(text, 0) + 1
            else:
                self._add_number(text)
        elif text.lower() in TEXT_MARKERS:
            self.markers[text] = self.markers.get(text, 0) + 1
        else:
            self._add_other(text, lineno)

    def _add_number(self, text: str) -> None:
        self.numeric += 1
        value = float(text)
        if self.min_value is None or value < self.min_value:
            self.min_value, self.min_text = value, text
        if self.max_value is None or value > self.max_value:
            self.max_value, self.max_text = value, text
        if "e" in text or "E" in text:
            return
        decimals = len(text) - text.index(".") - 1 if "." in text else 0
        if self.min_decimals is None or decimals < self.min_decimals:
            self.min_decimals = decimals
        if self.max_decimals is None or decimals > self.max_decimals:
            self.max_decimals = decimals

    def _add_other(self, text: str, lineno: int) -> None:
        self.other += 1
        if len(self.other_examples) < EXAMPLES and text not in self.other_examples:
            self.other_examples[text] = lineno

    def _add_time(self, text: str, lineno: int) -> None:
        try:
            stamp = datetime.fromisoformat(text)
        except ValueError:
            self._add_other(text, lineno)
            return
        self.numeric += 1
        if not self.first_time:
            self.first_time = text
        self.last_time = text
        prev = self._prev_time
        self._prev_time = stamp
        if prev is None:
            return
        try:
            if stamp == prev:
                self.time_repeats += 1
            elif stamp < prev:
                self.time_backwards += 1
                self.time_backwards_line = self.time_backwards_line or lineno
        except TypeError:
            self.time_mixed_offsets += 1


@dataclass(slots=True)
class TableProfile:
    """Statistics of one file; see :func:`profile_lines`."""

    total_lines: int = 0
    header_lineno: int = 0           # 0 = no header found
    preamble_lines: int = 0
    data_rows: int = 0
    empty_lines: int = 0
    comment_lines: int = 0
    crlf: int = 0
    lf: int = 0
    cr: int = 0
    has_bom: bool = False
    non_ascii_lines: int = 0
    invalid_lines: int = 0           # lines with bytes invalid in the encoding
    invalid_first_line: int = 0
    invalid_first_byte: int = 0
    ragged_rows: int = 0             # data rows whose cell count != header
    ragged_examples: list[int] = field(default_factory=list)
    ragged_min: int = 0
    ragged_max: int = 0
    columns: list[ColumnProfile] = field(default_factory=list)


def profile_lines(
    lines: Iterable[str],
    delimiter: str = "\t",
    header_line: int = 1,
    comment_prefix: str = "//",
) -> TableProfile:
    """Scan a file once and return its statistics.

    Args:
        lines:          Raw line stream *with* line endings, decoded with
                        ``errors="surrogateescape"`` (see module docstring).
        delimiter:      Column separator.
        header_line:    Earliest 1-based line the header may be on.
        comment_prefix: Prefix of comment lines.

    Returns:
        A :class:`TableProfile`.  ``header_lineno`` is 0 and ``columns`` is
        empty when no header line was found.
    """
    prof = TableProfile()
    is_header = header_finder(header_line, comment_prefix, delimiter)
    columns = prof.columns
    width = 0

    for lineno, raw in enumerate(lines, start=1):
        prof.total_lines = lineno
        if raw.endswith("\r\n"):
            prof.crlf += 1
            line = raw[:-2]
        elif raw.endswith("\n"):
            prof.lf += 1
            line = raw[:-1]
        elif raw.endswith("\r"):
            prof.cr += 1
            line = raw[:-1]
        else:
            line = raw
        if lineno == 1 and line.startswith("﻿"):
            prof.has_bom = True
            line = line[1:]
        if not line.isascii():
            prof.non_ascii_lines += 1
            bad = _INVALID_BYTE.search(line)
            if bad:
                prof.invalid_lines += 1
                if not prof.invalid_first_line:
                    prof.invalid_first_line = lineno
                    prof.invalid_first_byte = ord(bad.group()) - 0xDC00

        if not width:
            if not is_header(lineno, line):
                continue
            prof.header_lineno = lineno
            names = line.split(delimiter)
            width = len(names)
            columns.extend(
                ColumnProfile(i, name.strip(),
                              is_datetime=name.strip().lower().startswith("date/time"))
                for i, name in enumerate(names, start=1)
            )
            continue
        if line == "":
            prof.empty_lines += 1
            continue
        if is_comment(line, comment_prefix):
            prof.comment_lines += 1
            continue

        prof.data_rows += 1
        cells = line.split(delimiter)
        count = len(cells)
        if count != width:
            _note_ragged(prof, count, lineno)
            for column in columns[count:]:
                column.empty += 1
        for column, cell in zip(columns, cells):
            column.add(cell, lineno)

    prof.preamble_lines = (prof.header_lineno or prof.total_lines + 1) - 1
    return prof


def _note_ragged(prof: TableProfile, count: int, lineno: int) -> None:
    if not prof.ragged_rows:
        prof.ragged_min = prof.ragged_max = count
    prof.ragged_rows += 1
    prof.ragged_min = min(prof.ragged_min, count)
    prof.ragged_max = max(prof.ragged_max, count)
    if len(prof.ragged_examples) < EXAMPLES:
        prof.ragged_examples.append(lineno)


# ── Presentation ──────────────────────────────────────────────────────────────

COLUMN_HEADERS = [
    "No", "Column", "Type", "Filled", "Empty", "Numeric", "Min", "Max",
    "Decimals", "Distinct", "Missing-value markers", "Notes",
]


def summary_rows(prof: TableProfile, encoding: str = "UTF-8") -> list[tuple[str, str, bool]]:
    """Return ``(label, text, needs_attention)`` rows describing the file."""
    rows: list[tuple[str, str, bool]] = []

    if prof.invalid_lines:
        rows.append(("Encoding", (
            f"NOT valid {encoding}: {prof.invalid_lines:,} line(s) with invalid "
            f"bytes, first on line {prof.invalid_first_line:,} "
            f"(byte 0x{prof.invalid_first_byte:02X}). Try another input encoding."
        ), True))
    elif prof.non_ascii_lines:
        rows.append(("Encoding", (
            f"valid {encoding}, {prof.non_ascii_lines:,} line(s) with non-ASCII characters"
        ), False))
    else:
        rows.append(("Encoding", f"valid {encoding} (ASCII characters only)", False))
    if prof.has_bom:
        rows.append(("Byte-order mark", "present", False))

    endings = [(n, label) for n, label in
               ((prof.crlf, "CRLF"), (prof.lf, "LF"), (prof.cr, "CR")) if n]
    mixed = len(endings) > 1
    text = ", ".join(f"{label} ×{n:,}" for n, label in endings) if mixed else (
        endings[0][1] if endings else "none")
    rows.append(("Line endings", text + (" (mixed)" if mixed else ""), mixed))

    rows.append(("Lines", f"{prof.total_lines:,}", False))
    if not prof.header_lineno:
        rows.append(("Header", (
            "no header line containing the delimiter was found; "
            "check delimiter and header line in File › Options"
        ), True))
        return rows
    rows.append(("Header", (
        f"line {prof.header_lineno:,}, {len(prof.columns)} column(s)"
        + (f", {prof.preamble_lines:,} line(s) before it" if prof.preamble_lines else "")
    ), False))
    extras = "".join(
        f", {n:,} {label}" for n, label in
        ((prof.empty_lines, "empty line(s)"), (prof.comment_lines, "comment line(s)")) if n
    )
    rows.append(("Data rows", f"{prof.data_rows:,}{extras}", False))
    if prof.ragged_rows:
        span = (str(prof.ragged_min) if prof.ragged_min == prof.ragged_max
                else f"{prof.ragged_min}-{prof.ragged_max}")
        rows.append(("Row width", (
            f"{prof.ragged_rows:,} row(s) with {span} cells instead of "
            f"{len(prof.columns)}; first on line(s) "
            + ", ".join(f"{n:,}" for n in prof.ragged_examples)
        ), True))
    else:
        rows.append(("Row width", "all rows match the header", False))
    return rows


def column_rows(prof: TableProfile) -> list[tuple[list[str], bool]]:
    """Return one ``(cells, needs_attention)`` pair per column, matching
    :data:`COLUMN_HEADERS`."""
    rows: list[tuple[list[str], bool]] = []
    for col in prof.columns:
        notes: list[str] = []
        if col.other and (col.is_datetime or col.numeric):
            label = "not ISO 8601" if col.is_datetime else "non-numeric"
            examples = "; ".join(
                f"{value!r} (line {line:,})" for value, line in col.other_examples.items()
            )
            notes.append(f"{col.other:,} {label}: {examples}")
        if col.time_repeats:
            notes.append(f"{col.time_repeats:,} repeat(s) of the previous timestamp")
        if col.time_backwards:
            notes.append(f"{col.time_backwards:,} step(s) back in time, "
                         f"first on line {col.time_backwards_line:,}")
        if col.time_mixed_offsets:
            notes.append(f"{col.time_mixed_offsets:,} change(s) between timestamps "
                         "with and without UTC offset")
        if col.padded:
            notes.append(f"{col.padded:,} cell(s) with leading/trailing spaces")
        if col.kind == "text" and col.other_examples:
            notes.append("e.g. " + "; ".join(col.other_examples))

        if col.is_datetime:
            low, high = col.first_time, col.last_time
        else:
            low, high = col.min_text, col.max_text
        if col.min_decimals is None:
            decimals = ""
        elif col.min_decimals == col.max_decimals:
            decimals = str(col.max_decimals)
        else:
            decimals = f"{col.min_decimals}-{col.max_decimals}"
        markers = ", ".join(f"{m} ×{n:,}" for m, n in col.markers.items())
        attention = bool(
            col.markers or col.padded or col.time_backwards or col.time_repeats
            or col.time_mixed_offsets
            or (col.other and (col.is_datetime or col.numeric))
        )
        rows.append(([
            str(col.number), col.name, col.kind, f"{col.filled:,}", f"{col.empty:,}",
            "" if col.is_datetime else f"{col.numeric:,}", low, high, decimals,
            f">{DISTINCT_CAP:,}" if col.distinct is None else f"{col.distinct:,}",
            markers, " | ".join(notes),
        ], attention))
    return rows


def format_profile(
    prof: TableProfile,
    filename: str,
    encoding: str = "UTF-8",
    delimiter: str = "\t",
) -> Iterator[str]:
    """Yield the statistics as a delimited text report.

    Args:
        prof:      Result of :func:`profile_lines`.
        filename:  Name of the profiled file (first report line).
        encoding:  Input encoding the file was read with.
        delimiter: Column separator of the report.
    """
    yield delimiter.join(("File", filename))
    for label, text, _ in summary_rows(prof, encoding):
        yield delimiter.join((label, text))
    if not prof.columns:
        return
    yield ""
    yield delimiter.join(COLUMN_HEADERS)
    for cells, _ in column_rows(prof):
        yield delimiter.join(cells)
