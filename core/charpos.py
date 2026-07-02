"""Insert or replace characters at fixed character positions in every line.

Positions in user specs are 1-based (same convention as column specs) and may
be single numbers or ranges, e.g. ``"5,10-12"``.  Positions beyond the end of
a line append the text at the end, matching the original PanTool.
"""

from collections.abc import Iterable, Iterator


def parse_positions(spec: str) -> list[int]:
    """Parse a 1-based character-position spec into sorted unique 0-based indices.

    Args:
        spec: Comma-separated positions or ranges, e.g. ``"5,10-12"``.

    Raises:
        ValueError: If the spec is empty, contains non-integers, has positions
                    below 1, or a range with start > end.
    """
    if not spec.strip():
        raise ValueError("Position spec must not be empty.")

    indices: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            raw_lo, raw_hi = part.split("-", 1)
            lo = _parse_int(raw_lo)
            hi = _parse_int(raw_hi)
            if hi < lo:
                raise ValueError(f"Range start ({lo}) must be <= end ({hi}).")
            indices.update(range(lo - 1, hi))
        else:
            indices.add(_parse_int(part) - 1)

    if any(i < 0 for i in indices):
        raise ValueError("Positions must be 1 or greater.")
    return sorted(indices)


def insert_at_positions(lines: Iterable[str], spec: str, text: str) -> Iterator[str]:
    """Insert *text* before each character position of *spec* in every line.

    Args:
        lines: Input line stream (without trailing newlines).
        spec:  1-based position spec, e.g. ``"5,10-12"``.
        text:  String inserted at each position.
    """
    positions = parse_positions(spec)
    for line in lines:
        for pos in reversed(positions):
            line = line[:pos] + text + line[pos:]
        yield line


def replace_at_positions(lines: Iterable[str], spec: str, text: str) -> Iterator[str]:
    """Replace the character at each position of *spec* with *text* in every line.

    Args:
        lines: Input line stream (without trailing newlines).
        spec:  1-based position spec, e.g. ``"5,10-12"``.
        text:  Replacement string (may be empty to delete characters).
    """
    positions = parse_positions(spec)
    for line in lines:
        for pos in reversed(positions):
            line = line[:pos] + text + line[pos + 1:]
        yield line


def _parse_int(s: str) -> int:
    try:
        return int(s.strip())
    except ValueError:
        raise ValueError(f"Invalid position: {s!r}")
