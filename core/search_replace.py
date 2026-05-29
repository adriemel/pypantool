"""Search-and-replace tools.

``search_replace_one``  — replace a single search string across all lines.
``search_replace_many`` — apply a list of (search, replace) pairs in order.
``load_replacements``   — parse a replacement-database line stream into pairs.
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
