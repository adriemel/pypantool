"""Split one file into several output files.

All functions yield ``(file_index, line)`` pairs, where *file_index* is the
1-based number of the output chunk the line belongs to.  The GUI worker maps
each index to an output file named ``<stem>_<index:04d><ext>``.

``split_by_lines``   — fixed number of data lines per chunk (sequential indices).
``split_by_size``    — chunks capped by size and line count (sequential indices).
``split_by_columns`` — fixed columns plus N data columns per chunk; every input
                       line fans out to all chunks (interleaved indices).
"""

from collections.abc import Iterable, Iterator

from core.columns import parse_column_spec


def split_by_lines(
    lines: Iterable[str],
    lines_per_file: int,
    header_lines: int = 0,
) -> Iterator[tuple[int, str]]:
    """Split a line stream into chunks of *lines_per_file* data lines.

    The first *header_lines* lines are repeated at the top of every chunk.

    Args:
        lines:          Input line stream (without trailing newlines).
        lines_per_file: Number of data lines per output chunk.
        header_lines:   Number of leading lines repeated in each chunk.

    Yields:
        ``(1-based chunk index, line)`` pairs with monotonic indices.

    Raises:
        ValueError: If *lines_per_file* is below 1 or *header_lines* negative.
    """
    if lines_per_file < 1:
        raise ValueError("Lines per file must be 1 or greater.")

    def chunk_of(data_lineno: int) -> int:
        return (data_lineno - 1) // lines_per_file + 1

    yield from _split_sequential(lines, header_lines, chunk_of)


def split_by_size(
    lines: Iterable[str],
    max_bytes: int = 100_000_000,
    max_lines: int = 1_000_000,
    header_lines: int = 0,
) -> Iterator[tuple[int, str]]:
    """Split a line stream into chunks capped by size and line count.

    A new chunk starts as soon as the current one reaches *max_bytes*
    (approximated as characters + newline) or *max_lines* data lines.
    The first *header_lines* lines are repeated at the top of every chunk.

    Args:
        lines:        Input line stream (without trailing newlines).
        max_bytes:    Approximate maximum chunk size. Default 100 MB.
        max_lines:    Maximum data lines per chunk. Default 1,000,000.
        header_lines: Number of leading lines repeated in each chunk.

    Yields:
        ``(1-based chunk index, line)`` pairs with monotonic indices.

    Raises:
        ValueError: If a cap is below 1 or *header_lines* is negative.
    """
    if max_bytes < 1 or max_lines < 1:
        raise ValueError("Size and line caps must be 1 or greater.")

    state = {"chunk": 1, "size": 0, "count": 0}

    def chunk_of(_data_lineno: int) -> int:
        if state["count"] >= max_lines or state["size"] >= max_bytes:
            state["chunk"] += 1
            state["size"] = 0
            state["count"] = 0
        return state["chunk"]

    def on_line(line: str) -> None:
        state["size"] += len(line) + 1
        state["count"] += 1

    yield from _split_sequential(lines, header_lines, chunk_of, on_line)


def split_by_columns(
    lines: Iterable[str],
    columns_per_file: int,
    fixed_spec: str = "",
    delimiter: str = "\t",
) -> Iterator[tuple[int, str]]:
    """Split a table into chunks of *columns_per_file* data columns.

    Columns matching *fixed_spec* (same syntax as extract columns) are
    repeated at the front of every chunk; the remaining columns — starting
    after the last fixed column — are dealt out in order.  Lines without the
    delimiter (comments, empty lines) pass through unchanged to every chunk.

    Args:
        lines:            Input line stream (without trailing newlines).
        columns_per_file: Number of data columns per output chunk.
        fixed_spec:       Optional 1-based column spec repeated in each chunk.
        delimiter:        Column separator.

    Yields:
        ``(1-based chunk index, line)`` pairs, interleaved across chunks
        line by line.

    Raises:
        ValueError: If *columns_per_file* is below 1, the spec is invalid, or
                    no data columns remain after the fixed columns.
    """
    if columns_per_file < 1:
        raise ValueError("Columns per file must be 1 or greater.")

    it = iter(lines)
    first = next(it, None)
    if first is None:
        return

    total = len(first.split(delimiter))
    fixed = parse_column_spec(fixed_spec, total) if fixed_spec.strip() else []
    start = (fixed[-1] + 1) if fixed else 0

    if start >= total:
        raise ValueError("No data columns remain after the fixed columns.")

    chunk_ranges = [
        (lo, min(lo + columns_per_file, total))
        for lo in range(start, total, columns_per_file)
    ]

    def fan_out(line: str) -> Iterator[tuple[int, str]]:
        if delimiter not in line:
            for idx in range(1, len(chunk_ranges) + 1):
                yield idx, line
            return
        cells = line.split(delimiter)
        for idx, (lo, hi) in enumerate(chunk_ranges, start=1):
            picked = [cells[i] for i in fixed if i < len(cells)]
            picked += cells[lo:hi]
            yield idx, delimiter.join(picked)

    yield from fan_out(first)
    for line in it:
        yield from fan_out(line)


def _split_sequential(
    lines: Iterable[str],
    header_lines: int,
    chunk_of,
    on_line=None,
) -> Iterator[tuple[int, str]]:
    """Shared driver for line-based splits.

    Buffers the first *header_lines* lines and re-emits them whenever
    *chunk_of* advances to a new chunk index.
    """
    if header_lines < 0:
        raise ValueError("Header lines must be 0 or greater.")

    header: list[str] = []
    current = 0
    data_lineno = 0

    for line in lines:
        if len(header) < header_lines:
            header.append(line)
            continue
        data_lineno += 1
        chunk = chunk_of(data_lineno)
        if chunk != current:
            current = chunk
            for h in header:
                yield current, h
        if on_line is not None:
            on_line(line)
        yield current, line
