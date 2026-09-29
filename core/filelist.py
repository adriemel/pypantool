"""File-list export tool.

Emits a tab-delimited text file with one metadata row per loaded file:
name, full path, size in bytes, and last-modified timestamp.
"""

from collections.abc import Iterable, Iterator
from datetime import datetime
from pathlib import Path


def emit_filelist(
    files: Iterable[Path],
    delimiter: str = "\t",
) -> Iterator[str]:
    """Yield a header line followed by one metadata row per file path.

    Columns: ``Name``, ``Path``, ``Size (bytes)``, ``Modified``.

    Args:
        files:     Iterable of :class:`~pathlib.Path` objects to describe.
        delimiter: Column separator.  Defaults to tab.
    """
    yield delimiter.join(["Name", "Path", "Size (bytes)", "Modified"])
    for path in files:
        try:
            stat = path.stat()
            size = str(stat.st_size)
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except OSError:
            size = "N/A"
            mtime = "N/A"
        yield delimiter.join([path.name, str(path.parent), size, mtime])


def count_newlines(chunks: Iterable[bytes]) -> int:
    """Count text lines in a stream of raw byte chunks.

    A final line without a trailing newline is counted too.

    Args:
        chunks: Consecutive byte chunks of one file.
    """
    count = 0
    last = b""
    for chunk in chunks:
        count += chunk.count(b"\n")
        last = chunk
    if last and not last.endswith(b"\n"):
        count += 1
    return count
