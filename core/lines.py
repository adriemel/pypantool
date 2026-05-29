"""Line extraction and deletion tools.

All functions stream line-by-line and never accumulate the full file in memory.
Line numbers are 1-based, matching user expectations.
"""

import re
from collections.abc import Callable, Iterable, Iterator


# ── Spec parsing ──────────────────────────────────────────────────────────────

def _build_line_predicate(spec: str) -> Callable[[int], bool]:
    """Parse a line-number spec and return a predicate ``(1-based lineno) -> bool``.

    Spec syntax examples::

        "5"          → line 5 only
        "1-3"        → lines 1 through 3
        "1,3,5-7"    → lines 1, 3, and 5 through 7
        "10-end"     → line 10 to the last line of the file

    Args:
        spec: Comma-separated list of line numbers or ranges.

    Raises:
        ValueError: If the spec is empty, contains non-integers, or a range
                    has start > end.
    """
    if not spec.strip():
        raise ValueError("Line spec must not be empty.")

    specifics: set[int] = set()
    # Each entry: (start, end) where end is None for open-ended "to EOF" ranges.
    ranges: list[tuple[int, int | None]] = []

    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            raw_lo, raw_hi = part.split("-", 1)
            try:
                lo = int(raw_lo.strip())
            except ValueError:
                raise ValueError(f"Invalid line number in spec: {raw_lo!r}")
            raw_hi = raw_hi.strip().lower()
            if raw_hi == "end":
                ranges.append((lo, None))
            else:
                try:
                    hi = int(raw_hi)
                except ValueError:
                    raise ValueError(f"Invalid line number in spec: {raw_hi!r}")
                if hi < lo:
                    raise ValueError(
                        f"Range start ({lo}) must be <= end ({hi}) in spec."
                    )
                ranges.append((lo, hi))
        else:
            try:
                specifics.add(int(part))
            except ValueError:
                raise ValueError(f"Invalid line number in spec: {part!r}")

    if not specifics and not ranges:
        raise ValueError("Line spec produced no selectors.")

    def matches(lineno: int) -> bool:
        if lineno in specifics:
            return True
        for start, end in ranges:
            if end is None:
                if lineno >= start:
                    return True
            elif start <= lineno <= end:
                return True
        return False

    return matches


# ── Public functions ──────────────────────────────────────────────────────────

def extract_lines(lines: Iterable[str], spec: str) -> Iterator[str]:
    """Yield only the lines whose 1-based position matches *spec*.

    Args:
        lines: Input line stream (without trailing newlines).
        spec:  Line-number spec, e.g. ``"1-3,5,10-end"``.
    """
    matches = _build_line_predicate(spec)
    for lineno, line in enumerate(lines, start=1):
        if matches(lineno):
            yield line


def delete_lines(lines: Iterable[str], spec: str) -> Iterator[str]:
    """Yield all lines *except* those whose 1-based position matches *spec*.

    Args:
        lines: Input line stream (without trailing newlines).
        spec:  Line-number spec, e.g. ``"1-3,5,10-end"``.
    """
    matches = _build_line_predicate(spec)
    for lineno, line in enumerate(lines, start=1):
        if not matches(lineno):
            yield line


def extract_matched_lines(
    lines: Iterable[str],
    pattern: str,
    is_regex: bool = False,
) -> Iterator[str]:
    """Yield lines that contain *pattern* (substring or regex).

    Args:
        lines:    Input line stream.
        pattern:  Search string or regular expression.
        is_regex: When ``True``, *pattern* is compiled as a regex.
    """
    if is_regex:
        rx = re.compile(pattern)
        for line in lines:
            if rx.search(line):
                yield line
    else:
        for line in lines:
            if pattern in line:
                yield line


def delete_matched_lines(
    lines: Iterable[str],
    pattern: str,
    is_regex: bool = False,
) -> Iterator[str]:
    """Yield lines that do *not* contain *pattern* (substring or regex).

    Args:
        lines:    Input line stream.
        pattern:  Search string or regular expression.
        is_regex: When ``True``, *pattern* is compiled as a regex.
    """
    if is_regex:
        rx = re.compile(pattern)
        for line in lines:
            if not rx.search(line):
                yield line
    else:
        for line in lines:
            if pattern not in line:
                yield line
