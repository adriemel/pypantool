"""Insert one or more text lines at a given line number.

Covers both "Add text line" (one line) and "Add text block" (multiple lines).
"""

from collections.abc import Iterable, Iterator


def add_lines(
    lines: Iterable[str],
    text_lines: list[str],
    line_no: int = 1,
) -> Iterator[str]:
    """Insert *text_lines* so the block starts at 1-based line number *line_no*.

    If the file has fewer than *line_no* lines, the block is appended at the
    end instead.

    Args:
        lines:      Input line stream (without trailing newlines).
        text_lines: Lines to insert, in order.
        line_no:    1-based line number where the inserted block starts.

    Raises:
        ValueError: If *line_no* is below 1 or *text_lines* is empty.
    """
    if line_no < 1:
        raise ValueError("Line number must be 1 or greater.")
    if not text_lines:
        raise ValueError("Text to insert must not be empty.")

    inserted = False
    for lineno, line in enumerate(lines, start=1):
        if lineno == line_no:
            yield from text_lines
            inserted = True
        yield line

    if not inserted:
        yield from text_lines
