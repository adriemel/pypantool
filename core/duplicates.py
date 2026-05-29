"""Duplicate-line removal tool.

Uses SHA-256 hashes of the raw line text to track seen lines without storing
the line content itself, keeping memory bounded regardless of file size.
"""

import hashlib
from collections.abc import Iterable, Iterator


def delete_double_lines(lines: Iterable[str]) -> Iterator[str]:
    """Yield each unique line once, discarding subsequent duplicates.

    Comparison is exact (case-sensitive, whitespace-significant). First
    occurrence is kept; later identical lines are dropped. Uses SHA-256
    hashes — no line text is stored after hashing.

    Args:
        lines: Input line stream (without trailing newlines).
    """
    seen: set[bytes] = set()
    for line in lines:
        digest = hashlib.sha256(line.encode()).digest()
        if digest not in seen:
            seen.add(digest)
            yield line
