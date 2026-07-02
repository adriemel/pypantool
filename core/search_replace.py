"""Search-and-replace tools.

``search_replace_one``  — replace a single search string across all lines.
``search_replace_many`` — apply a list of (search, replace) pairs in order.
``load_replacements``   — parse a replacement-database line stream into pairs.
``search_one_string``   — report every match across many files (no replacing).
"""

from collections.abc import Iterable, Iterator


def search_replace_one(
    lines: Iterable[str],
    search: str,
    replace: str,
) -> Iterator[str]:
    """Replace every occurrence of *search* with *replace* in each line.

    The replacement is plain substring replacement (not regex).  All
    occurrences within a line are replaced.

    Args:
        lines:   Input line stream (without trailing newlines).
        search:  String to search for.
        replace: String to substitute.

    Raises:
        ValueError: If *search* is empty.
    """
    if not search:
        raise ValueError("Search string must not be empty.")

    for line in lines:
        yield line.replace(search, replace)


def search_replace_many(
    lines: Iterable[str],
    replacements: list[tuple[str, str]],
) -> Iterator[str]:
    """Apply a sequence of ``(search, replace)`` pairs to every line.

    Pairs are applied in order: the output of one replacement becomes the
    input for the next.  All replacements are plain substring replacements.

    Args:
        lines:        Input line stream (without trailing newlines).
        replacements: Ordered list of ``(search_string, replacement_string)``
                      pairs.  Pairs whose search string is empty are silently
                      skipped.
    """
    active = [(s, r) for s, r in replacements if s]  # drop empty searches

    for line in lines:
        for search, replace in active:
            line = line.replace(search, replace)
        yield line


def search_one_string(
    inputs: Iterable[tuple[str, Iterable[str]]],
    search: str,
    start_line: int = 1,
    num_lines: int = 0,
    delimiter: str = "\t",
) -> Iterator[str]:
    """Report every line containing *search* across multiple files.

    Produces a delimited report with a header row followed by one row per
    match: filename, 1-based line number, and the matching line.

    Args:
        inputs:     Iterable of ``(filename, line_stream)`` pairs.
        search:     Substring to look for (plain match, not regex).
        start_line: 1-based line number where the search starts in each file.
        num_lines:  Number of lines to search per file; 0 searches to the end.
        delimiter:  Column separator for the report.

    Raises:
        ValueError: If *search* is empty or *start_line* is below 1.
    """
    if not search:
        raise ValueError("Search string must not be empty.")
    if start_line < 1:
        raise ValueError("Start line must be 1 or greater.")

    yield delimiter.join(("Filename", "Line", "String"))

    end_line = start_line + num_lines - 1 if num_lines > 0 else None
    for name, lines in inputs:
        for lineno, line in enumerate(lines, start=1):
            if lineno < start_line:
                continue
            if end_line is not None and lineno > end_line:
                break
            if search in line:
                yield delimiter.join((name, str(lineno), line))


def load_replacements(
    lines: Iterable[str],
    delimiter: str = "\t",
) -> list[tuple[str, str]]:
    """Parse a replacement-database line stream into ``(search, replace)`` pairs.

    The database format is a delimited text file: first column is the search
    string, second column is the replacement string.  Blank lines are skipped.
    Lines that contain no delimiter are skipped (they cannot form a valid pair).

    Args:
        lines:     Line stream from the database file (without trailing newlines).
        delimiter: Column separator.  Defaults to tab.

    Returns:
        List of ``(search, replace)`` tuples in file order.
    """
    pairs: list[tuple[str, str]] = []
    for line in lines:
        if not line:
            continue
        parts = line.split(delimiter, 1)
        if len(parts) == 2:
            pairs.append((parts[0], parts[1]))
    return pairs
