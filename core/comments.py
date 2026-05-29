"""Comment-block deletion tool.

Removes lines whose content starts with a configurable prefix string.
"""

from collections.abc import Iterable, Iterator


def delete_comments(lines: Iterable[str], prefix: str = "//") -> Iterator[str]:
    """Yield all lines that do *not* start with *prefix*.

    Args:
        lines:  Input line stream (without trailing newlines).
        prefix: Comment prefix to filter out. Default is ``"//"``.

    Raises:
        ValueError: If *prefix* is empty.
    """
    if not prefix:
        raise ValueError("Comment prefix must not be empty.")

    for line in lines:
        if not line.startswith(prefix):
            yield line
