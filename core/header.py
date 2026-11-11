"""Shared detection of the column-header line of a tabular text file.

Every column-aware tool uses the same rule, so a file is interpreted the same
way by all of them.  The header is the first line that

- is not inside a leading ``/* ... */`` metadata block (PANGAEA downloads),
- is at or after the configured 1-based *header_line*,
- does not start with the comment prefix, and
- contains the delimiter.

Everything before the header is "preamble" and is never column-processed.
"""

from collections.abc import Callable


def header_finder(
    header_line: int = 1,
    comment_prefix: str = "//",
    delimiter: str = "\t",
    require_delimiter: bool = True,
) -> Callable[[int, str], bool]:
    """Return a stateful predicate ``(1-based lineno, line) -> is this the header?``.

    Call it once per line, in file order, until it returns ``True``.

    Args:
        header_line:    Earliest line number the header may be on.
        comment_prefix: Lines starting with this are never the header
                        (empty string disables the check).
        delimiter:      Column separator; the header must contain it.
        require_delimiter: Set ``False`` to accept single-column headers.

    Raises:
        ValueError: If *header_line* is below 1.
    """
    if header_line < 1:
        raise ValueError("Header line must be 1 or greater.")

    in_block = False

    def is_header(lineno: int, line: str) -> bool:
        nonlocal in_block
        if in_block:
            in_block = "*/" not in line
            return False
        if lineno == 1 and line.startswith("/*"):
            in_block = "*/" not in line
            return False
        if lineno < header_line:
            return False
        if is_comment(line, comment_prefix):
            return False
        return delimiter in line or (bool(line) and not require_delimiter)

    return is_header


def is_comment(line: str, comment_prefix: str) -> bool:
    """True if *line* starts with a non-empty *comment_prefix*."""
    return bool(comment_prefix) and line.startswith(comment_prefix)
