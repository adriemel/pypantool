"""Read only the beginning of a file: peek pane, quick sniff, dialog previews.

Nothing here reads more than a fixed number of bytes, so it is safe for
files of any size.
"""

import io
from pathlib import Path

from core.header import header_finder, is_comment
from core.profile import TableProfile, profile_lines

PEEK_LINES = 200
PEEK_BYTES = 262_144
SNIFF_BYTES = 65_536


def _codec(encoding: str, drop_bom: bool = True) -> str:
    if drop_bom and encoding.upper().replace("-", "") == "UTF8":
        return "utf-8-sig"
    return encoding


def head_lines(
    path: Path,
    encoding: str,
    max_lines: int = PEEK_LINES,
    max_bytes: int = PEEK_BYTES,
    errors: str = "replace",
    keepends: bool = False,
) -> list[str]:
    """Return up to *max_lines* complete lines from the first *max_bytes* of *path*.

    Raises:
        OSError: If the file cannot be read.
    """
    with open(path, "rb") as fh:
        data = fh.read(max_bytes)
        truncated = bool(fh.read(1))
    wrapper = io.TextIOWrapper(
        io.BytesIO(data), encoding=_codec(encoding, drop_bom=not keepends),
        errors=errors, newline="" if keepends else None,
    )
    lines = list(wrapper) if keepends else [line.rstrip("\n") for line in wrapper]
    if truncated and len(lines) > 1:
        lines.pop()  # last line is cut off
    return lines[:max_lines]


def sniff(path: Path, encoding: str, options: dict) -> TableProfile:
    """Profile the first 64 kB of *path* (columns, encoding, line endings)."""
    lines = head_lines(path, encoding, max_lines=10**9, max_bytes=SNIFF_BYTES,
                       errors="surrogateescape", keepends=True)
    return profile_lines(lines, **options)


def header_and_first_row(
    path: Path, encoding: str, options: dict,
) -> tuple[str, str] | None:
    """Return (header line, first data line) of *path*, or None if not found."""
    is_header = header_finder(options["header_line"], options["comment_prefix"],
                              options["delimiter"], require_delimiter=False)
    try:
        lines = head_lines(path, encoding, max_lines=10_000, max_bytes=1_048_576)
    except OSError:
        return None
    header: str | None = None
    for lineno, line in enumerate(lines, start=1):
        if header is None:
            if is_header(lineno, line):
                header = line
        elif line and not is_comment(line, options["comment_prefix"]):
            return header, line
    return None
