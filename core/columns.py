"""Column extraction and deletion tools.

Design rules:
- Lines that contain the delimiter are treated as tabular and get column-filtered.
- Lines without the delimiter (comments, empty lines) are always passed through
  unchanged, regardless of where they appear in the stream.
- Column count is resolved from the first delimited line encountered.
- For matched-column variants, the header is the first delimited line that does
  not start with the comment prefix ``//``.
- Column numbers in user specs are 1-based; internally everything is 0-based.
"""

import re
from collections.abc import Callable, Iterable, Iterator


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
        ValueError: If the spec is empty, contains non-integers, or a range
                    has start > end.
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
                raise ValueError(
                    f"Range start ({lo}) must be <= end ({raw_hi})."
                )
            for i in range(lo - 1, hi):  # convert to 0-based
                indices.add(i)
        else:
            low = part.strip().lower()
            if low == "end":
                indices.add(total - 1)
            else:
                indices.add(_parse_int(part) - 1)  # convert to 0-based

    return sorted(indices)


def _parse_int(s: str) -> int:
    try:
        return int(s)
    except ValueError:
        raise ValueError(f"Invalid column number: {s!r}")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _make_picker(indices: list[int], delimiter: str) -> Callable[[str], str]:
    """Return a function that extracts *indices* from a delimited line.

    Lines that do not contain *delimiter* are returned unchanged.
    """
    def pick(line: str) -> str:
        if delimiter not in line:
            return line
        parts = line.split(delimiter)
        return delimiter.join(parts[i] for i in indices if i < len(parts))
    return pick


def _make_matcher(pattern: str, is_regex: bool) -> Callable[[str], bool]:
    if is_regex:
        rx = re.compile(pattern)
        return lambda s: bool(rx.search(s))
    return lambda s: pattern in s


# ── extract / delete by spec ──────────────────────────────────────────────────

def extract_columns(
    lines: Iterable[str],
    spec: str,
    delimiter: str = "\t",
) -> Iterator[str]:
    """Yield each line keeping only the columns specified by *spec*.

    Lines without *delimiter* (e.g. comment or empty lines) are passed through
    unchanged.  Column count is determined from the first delimited line.

    Args:
        lines:     Input line stream (without trailing newlines).
        spec:      Column spec, e.g. ``"1-3,5-end"``. Numbers are 1-based.
        delimiter: Field separator (default tab).
    """
    it = iter(lines)
    pick: Callable[[str], str] | None = None

    for line in it:
        if delimiter not in line:
            yield line
            continue
        if pick is None:
            total = len(line.split(delimiter))
            pick = _make_picker(parse_column_spec(spec, total), delimiter)
        yield pick(line)


def delete_columns(
    lines: Iterable[str],
    spec: str,
    delimiter: str = "\t",
) -> Iterator[str]:
    """Yield each line with the columns specified by *spec* removed.

    Lines without *delimiter* are passed through unchanged.

    Args:
        lines:     Input line stream.
        spec:      Column spec for the columns to *remove*.
        delimiter: Field separator (default tab).
    """
    it = iter(lines)
    pick: Callable[[str], str] | None = None

    for line in it:
        if delimiter not in line:
            yield line
            continue
        if pick is None:
            total = len(line.split(delimiter))
            delete_set = set(parse_column_spec(spec, total))
            keep = [i for i in range(total) if i not in delete_set]
            pick = _make_picker(keep, delimiter)
        yield pick(line)


# ── extract / delete by header match ─────────────────────────────────────────

def extract_matched_columns(
    lines: Iterable[str],
    pattern: str,
    is_regex: bool = False,
    delimiter: str = "\t",
) -> Iterator[str]:
    """Yield each line keeping only columns whose header matches *pattern*.

    The header is the first delimited line that does not start with ``//``.
    Lines before the header (comment/empty lines) are passed through unchanged.
    Lines without *delimiter* that appear after the header are also passed
    through unchanged.

    Args:
        lines:     Input line stream.
        pattern:   Substring or regex to match against column header names.
        is_regex:  When ``True``, *pattern* is compiled as a regular expression.
        delimiter: Field separator (default tab).
    """
    it = iter(lines)
    matches = _make_matcher(pattern, is_regex)

    for line in it:
        # Pre-header: comment/empty lines without column structure.
        if delimiter not in line or line.startswith("//"):
            yield line
            continue

        # First real header found — build index list from matching headers.
        headers = line.split(delimiter)
        indices = [i for i, h in enumerate(headers) if matches(h)]
        pick = _make_picker(indices, delimiter)

        yield pick(line)
        for remaining in it:
            yield pick(remaining)
        return


def delete_matched_columns(
    lines: Iterable[str],
    pattern: str,
    is_regex: bool = False,
    delimiter: str = "\t",
) -> Iterator[str]:
    """Yield each line with columns whose header matches *pattern* removed.

    Args:
        lines:     Input line stream.
        pattern:   Substring or regex to match against column header names.
        is_regex:  When ``True``, *pattern* is compiled as a regular expression.
        delimiter: Field separator (default tab).
    """
    it = iter(lines)
    matches = _make_matcher(pattern, is_regex)

    for line in it:
        if delimiter not in line or line.startswith("//"):
            yield line
            continue

        headers = line.split(delimiter)
        delete_set = {i for i, h in enumerate(headers) if matches(h)}
        keep = [i for i in range(len(headers)) if i not in delete_set]
        pick = _make_picker(keep, delimiter)

        yield pick(line)
        for remaining in it:
            yield pick(remaining)
        return
