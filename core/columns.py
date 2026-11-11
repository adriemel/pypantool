"""Column extraction and deletion tools.

Design rules:
- The header line is located by :func:`core.header.header_finder` (same rule
  for every column-aware tool).  Lines before it pass through unchanged.
- The column count is taken from the header line.
- From the header on, lines that contain the delimiter get column-filtered.
  Comment lines and lines without the delimiter pass through unchanged.
- Rows shorter than the header are padded with empty cells when extracting,
  so values never shift into another column.
- Column numbers in user specs are 1-based; internally everything is 0-based.
"""

import re
from collections.abc import Callable, Iterable, Iterator

from core.header import header_finder, is_comment


# ── Spec parsing ──────────────────────────────────────────────────────────────

def parse_column_spec(spec: str, total: int) -> list[int]:
    """Parse a column-number spec into sorted unique 0-based indices.

    Args:
        spec:  Comma-separated column numbers/ranges, e.g. ``"3,5-end"``.
               Column numbers are 1-based; ``end`` refers to the last column.
        total: Total number of columns, used only to resolve ``end``.

    Returns:
        Sorted list of unique 0-based column indices.

    Raises:
        ValueError: If the spec is empty, contains non-integers, a range has
                    start > end, or a column is below 1 or above *total*.
    """
    if not spec.strip():
        raise ValueError("Column spec must not be empty.")

    indices: set[int] = set()

    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            raw_lo, raw_hi = part.split("-", 1)
            try:
                lo = int(raw_lo.strip())
            except ValueError:
                raise ValueError(f"Invalid column number: {raw_lo!r}")
            raw_hi = raw_hi.strip().lower()
            hi = total if raw_hi == "end" else _parse_int(raw_hi)
            if hi < lo:
                shown = f"end = {total}" if raw_hi == "end" else raw_hi
                raise ValueError(
                    f"Range start ({lo}) must be <= end ({shown})."
                )
            for i in range(lo - 1, hi):  # convert to 0-based
                indices.add(i)
        else:
            low = part.strip().lower()
            if low == "end":
                indices.add(total - 1)
            else:
                indices.add(_parse_int(part) - 1)  # convert to 0-based

    if not indices:
        raise ValueError("Column spec must not be empty.")
    if min(indices) < 0:
        raise ValueError("Column numbers must be 1 or greater.")
    if max(indices) >= total:
        raise ValueError(
            f"Column {max(indices) + 1} does not exist: the header line has "
            f"{total} column(s)."
        )
    return sorted(indices)


def _parse_int(s: str) -> int:
    try:
        return int(s)
    except ValueError:
        raise ValueError(f"Invalid column number: {s!r}")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _make_matcher(pattern: str, is_regex: bool) -> Callable[[str], bool]:
    if is_regex:
        rx = re.compile(pattern)
        return lambda s: bool(rx.search(s))
    return lambda s: pattern in s


def _filter_columns(
    lines: Iterable[str],
    choose: Callable[[list[str]], list[int]],
    keep_chosen: bool,
    delimiter: str,
    header_line: int,
    comment_prefix: str,
) -> Iterator[str]:
    """Shared driver: locate the header, let *choose* pick 0-based column
    indices from its cells, then keep or drop those columns on every row."""
    is_header = header_finder(header_line, comment_prefix, delimiter)
    chosen: list[int] | None = None
    chosen_set: set[int] = set()

    for lineno, line in enumerate(lines, start=1):
        if chosen is None:
            if not is_header(lineno, line):
                yield line
                continue
            chosen = choose(line.split(delimiter))
            chosen_set = set(chosen)
        elif delimiter not in line or is_comment(line, comment_prefix):
            yield line
            continue

        parts = line.split(delimiter)
        if keep_chosen:
            n = len(parts)
            yield delimiter.join(parts[i] if i < n else "" for i in chosen)
        else:
            yield delimiter.join(
                cell for i, cell in enumerate(parts) if i not in chosen_set
            )


# ── extract / delete by spec ──────────────────────────────────────────────────

def extract_columns(
    lines: Iterable[str],
    spec: str,
    delimiter: str = "\t",
    header_line: int = 1,
    comment_prefix: str = "//",
) -> Iterator[str]:
    """Yield each line keeping only the columns specified by *spec*.

    Lines before the header, comment lines and lines without *delimiter* are
    passed through unchanged.  Rows shorter than the header are padded with
    empty cells.

    Args:
        lines:          Input line stream (without trailing newlines).
        spec:           Column spec, e.g. ``"1-3,5-end"``. Numbers are 1-based.
        delimiter:      Field separator (default tab).
        header_line:    Earliest 1-based line the header may be on.
        comment_prefix: Prefix of comment lines.

    Raises:
        ValueError: If *spec* is invalid for the header's column count.
    """
    yield from _filter_columns(
        lines, lambda cells: parse_column_spec(spec, len(cells)),
        True, delimiter, header_line, comment_prefix,
    )


def delete_columns(
    lines: Iterable[str],
    spec: str,
    delimiter: str = "\t",
    header_line: int = 1,
    comment_prefix: str = "//",
) -> Iterator[str]:
    """Yield each line with the columns specified by *spec* removed.

    Lines before the header, comment lines and lines without *delimiter* are
    passed through unchanged.

    Args:
        lines:          Input line stream.
        spec:           Column spec for the columns to *remove*.
        delimiter:      Field separator (default tab).
        header_line:    Earliest 1-based line the header may be on.
        comment_prefix: Prefix of comment lines.

    Raises:
        ValueError: If *spec* is invalid for the header's column count.
    """
    yield from _filter_columns(
        lines, lambda cells: parse_column_spec(spec, len(cells)),
        False, delimiter, header_line, comment_prefix,
    )


# ── extract / delete by header match ─────────────────────────────────────────

def _matching(pattern: str, is_regex: bool) -> Callable[[list[str]], list[int]]:
    matches = _make_matcher(pattern, is_regex)

    def choose(cells: list[str]) -> list[int]:
        found = [i for i, cell in enumerate(cells) if matches(cell)]
        if not found:
            raise ValueError(f"No column header matches {pattern!r}.")
        return found

    return choose


def extract_matched_columns(
    lines: Iterable[str],
    pattern: str,
    is_regex: bool = False,
    delimiter: str = "\t",
    header_line: int = 1,
    comment_prefix: str = "//",
) -> Iterator[str]:
    """Yield each line keeping only columns whose header matches *pattern*.

    Lines before the header, comment lines and lines without *delimiter* are
    passed through unchanged.

    Args:
        lines:          Input line stream.
        pattern:        Substring or regex to match against column header names.
        is_regex:       When ``True``, *pattern* is compiled as a regular expression.
        delimiter:      Field separator (default tab).
        header_line:    Earliest 1-based line the header may be on.
        comment_prefix: Prefix of comment lines.

    Raises:
        ValueError: If no header cell matches *pattern*.
    """
    yield from _filter_columns(
        lines, _matching(pattern, is_regex),
        True, delimiter, header_line, comment_prefix,
    )


def delete_matched_columns(
    lines: Iterable[str],
    pattern: str,
    is_regex: bool = False,
    delimiter: str = "\t",
    header_line: int = 1,
    comment_prefix: str = "//",
) -> Iterator[str]:
    """Yield each line with columns whose header matches *pattern* removed.

    Args:
        lines:          Input line stream.
        pattern:        Substring or regex to match against column header names.
        is_regex:       When ``True``, *pattern* is compiled as a regular expression.
        delimiter:      Field separator (default tab).
        header_line:    Earliest 1-based line the header may be on.
        comment_prefix: Prefix of comment lines.

    Raises:
        ValueError: If no header cell matches *pattern*.
    """
    yield from _filter_columns(
        lines, _matching(pattern, is_regex),
        False, delimiter, header_line, comment_prefix,
    )
