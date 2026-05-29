"""File concatenation tools.

Two strategies:
- ``concat_by_lines``:   append files top-to-bottom (vertical stack).
- ``concat_by_columns``: merge files side-by-side (horizontal zip).

Both accept an iterable of ``(filename, line_stream)`` pairs so the caller
controls how files are opened, making the functions fully testable without
touching the filesystem.
"""

from collections.abc import Iterable, Iterator


def concat_by_lines(
    inputs: Iterable[tuple[str, Iterable[str]]],
    skip_header_lines: int = 0,
    include_filename: bool = False,
    skip_empty: bool = False,
    skip_comments: bool = False,
    comment_prefix: str = "//",
) -> Iterator[str]:
    """Append files top-to-bottom.

    Args:
        inputs:            Iterable of ``(filename, line_stream)`` pairs.
        skip_header_lines: Number of lines to skip from files 2..N (avoids
                           duplicate column headers).
        include_filename:  If True, emit ``# {filename}`` before each file's
                           block.
        skip_empty:        If True, suppress blank lines in the output.
        skip_comments:     If True, suppress lines starting with
                           *comment_prefix*.
        comment_prefix:    Prefix that identifies a comment line. Only used
                           when *skip_comments* is True.

    Raises:
        ValueError: If *skip_comments* is True and *comment_prefix* is empty.
    """
    if skip_comments and not comment_prefix:
        raise ValueError("comment_prefix must not be empty when skip_comments is True.")

    for file_idx, (name, lines) in enumerate(inputs):
        if include_filename:
            yield f"# {name}"

        it = iter(lines)

        # Skip header lines from files 2..N.
        if file_idx > 0:
            for _ in range(skip_header_lines):
                try:
                    next(it)
                except StopIteration:
                    break

        for line in it:
            if skip_empty and line == "":
                continue
            if skip_comments and line.startswith(comment_prefix):
                continue
            yield line


def concat_by_columns(
    inputs: Iterable[tuple[str, Iterable[str]]],
    delimiter: str = "\t",
    skip_header_lines: int = 0,
    include_filename_row: bool = False,
) -> Iterator[str]:
    """Merge files side-by-side (horizontal zip).

    Every input file must have the same number of rows after header skipping.
    Row *i* from each file is joined with *delimiter* to form one output row.

    Args:
        inputs:              Iterable of ``(filename, line_stream)`` pairs.
        delimiter:           Character used to join columns from different
                             files. Should match the file's own delimiter.
        skip_header_lines:   Number of leading lines to skip from *all* files
                             before zipping.  Skipped lines are not emitted.
        include_filename_row: If True, emit one row of filenames (joined by
                              *delimiter*) as the very first output line.

    Raises:
        ValueError: If the files have different row counts after header
                    skipping, or if no inputs are provided.
    """
    pairs = [(name, iter(lines)) for name, lines in inputs]
    if not pairs:
        return

    if include_filename_row:
        yield delimiter.join(name for name, _ in pairs)

    # Discard skip_header_lines from every file.
    for _ in range(skip_header_lines):
        for _, it in pairs:
            try:
                next(it)
            except StopIteration:
                pass  # file already exhausted during header skip

    # Zip remaining rows; detect row-count mismatches.
    _SENTINEL = object()
    row_num = 0
    while True:
        parts: list[str] = []
        short: list[str] = []

        for name, it in pairs:
            val = next(it, _SENTINEL)
            if val is _SENTINEL:
                short.append(name)
            else:
                parts.append(val)  # type: ignore[arg-type]

        if len(short) == len(pairs):
            break  # all files exhausted simultaneously — normal end

        if short:
            raise ValueError(
                f"Files have unequal row counts after header skip: "
                f"{short} ended at row {row_num + 1}."
            )

        yield delimiter.join(parts)
        row_num += 1
