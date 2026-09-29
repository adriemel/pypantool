"""File concatenation tools.

Two strategies:
- ``concat_by_lines``:   append files top-to-bottom (vertical stack).
- ``concat_by_columns``: merge files side-by-side (horizontal zip).

Both accept an iterable of ``(filename, line_stream)`` pairs so the caller
controls how files are opened, making the functions fully testable without
touching the filesystem.
"""

from collections.abc import Iterable, Iterator
from pathlib import PurePath

FILENAME_HEADER = "Filename"


def concat_by_lines(
    inputs: Iterable[tuple[str, Iterable[str]]],
    skip_header_lines: int = 0,
    filename_column: bool = False,
    skip_empty: bool = False,
    skip_comments: bool = False,
    comment_prefix: str = "//",
    delimiter: str = "\t",
) -> Iterator[str]:
    """Append files top-to-bottom.

    Args:
        inputs:            Iterable of ``(filename, line_stream)`` pairs.
        skip_header_lines: Number of header lines. They are kept from the
                           first file and skipped from files 2..N (avoids
                           duplicate column headers).
        filename_column:   If True, prepend the file stem as column 1 of
                           every data line.  The last header line of the
                           first file gets ``Filename`` instead.  Comment
                           lines (*comment_prefix*) and empty lines are
                           never prefixed.
        skip_empty:        If True, suppress blank lines in the output.
        skip_comments:     If True, suppress lines starting with
                           *comment_prefix*.
        comment_prefix:    Prefix that identifies a comment line.
        delimiter:         Column separator used for the filename column.

    Raises:
        ValueError: If *skip_comments* is True and *comment_prefix* is empty.
    """
    if skip_comments and not comment_prefix:
        raise ValueError("comment_prefix must not be empty when skip_comments is True.")

    def is_comment(line: str) -> bool:
        return bool(comment_prefix) and line.startswith(comment_prefix)

    for file_idx, (name, lines) in enumerate(inputs):
        stem = PurePath(name).stem
        for lineno, line in enumerate(lines, start=1):
            is_header = lineno <= skip_header_lines
            if is_header and file_idx > 0:
                continue
            if skip_empty and line == "":
                continue
            if skip_comments and is_comment(line):
                continue
            if not filename_column or line == "" or is_comment(line):
                yield line
            elif not is_header:
                yield f"{stem}{delimiter}{line}"
            elif lineno == skip_header_lines:
                yield f"{FILENAME_HEADER}{delimiter}{line}"
            else:
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
