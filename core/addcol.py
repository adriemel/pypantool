"""Add a constant column and/or metadata columns to every line.

The first line is treated as the header: it receives *header_text* and the
metadata column names (``Event label``, ``Filename``, ``No``).  Data lines
receive *column_text*, the file's name/path, and a 1-based ordinal number.
"""

from collections.abc import Iterable, Iterator
from pathlib import Path


def add_column(
    lines: Iterable[str],
    in_path: Path | None = None,
    *,
    header_text: str = "",
    column_text: str = "",
    position: str = "append",
    add_filename: bool = False,
    add_full_path: bool = False,
    add_ordinal: bool = False,
    meta_position: str = "prepend",
    delimiter: str = "\t",
) -> Iterator[str]:
    """Add a user column and/or metadata columns to every line.

    Args:
        lines:         Input line stream (without trailing newlines).
        in_path:       Path of the current input file; used for the filename
                       and full-path metadata columns.
        header_text:   Header cell for the user column.
        column_text:   Data cell repeated on every data line.
        position:      ``"prepend"`` or ``"append"`` — where the user column goes.
        add_filename:  Add an ``Event label`` column with the file stem.
        add_full_path: Add a ``Filename`` column with the absolute path.
        add_ordinal:   Add a ``No`` column with a 1-based data line counter.
        meta_position: ``"prepend"`` or ``"append"`` — where metadata columns go.
        delimiter:     Column separator.

    Raises:
        ValueError: If *position* or *meta_position* is invalid, or nothing
                    was selected to add.
    """
    for name, value in (("position", position), ("meta_position", meta_position)):
        if value not in ("prepend", "append"):
            raise ValueError(f"{name} must be 'prepend' or 'append', not {value!r}.")

    add_user_column = bool(header_text or column_text)
    add_meta = add_filename or add_full_path or add_ordinal
    if not add_user_column and not add_meta:
        raise ValueError("Nothing to add: enter column text or select a metadata column.")

    stem = in_path.stem if in_path else ""
    full = str(in_path.resolve()) if in_path else ""

    it = iter(lines)
    header = next(it, None)
    if header is None:
        return

    meta_header = _meta_cells(add_filename, add_full_path, add_ordinal,
                              "Event label", "Filename", "No")
    yield _assemble(header, header_text if add_user_column else None,
                    position, meta_header if add_meta else None,
                    meta_position, delimiter)

    for ordinal, line in enumerate(it, start=1):
        meta = _meta_cells(add_filename, add_full_path, add_ordinal,
                           stem, full, str(ordinal))
        yield _assemble(line, column_text if add_user_column else None,
                        position, meta if add_meta else None,
                        meta_position, delimiter)


def _meta_cells(
    add_filename: bool, add_full_path: bool, add_ordinal: bool,
    filename_value: str, path_value: str, ordinal_value: str,
) -> list[str]:
    cells: list[str] = []
    if add_filename:
        cells.append(filename_value)
    if add_full_path:
        cells.append(path_value)
    if add_ordinal:
        cells.append(ordinal_value)
    return cells


def _assemble(
    line: str,
    user_cell: str | None,
    position: str,
    meta_cells: list[str] | None,
    meta_position: str,
    delimiter: str,
) -> str:
    prepend: list[str] = []
    append: list[str] = []

    if meta_cells:
        (prepend if meta_position == "prepend" else append).extend(meta_cells)
    if user_cell is not None:
        if position == "prepend":
            prepend.append(user_cell)
        else:
            append.append(user_cell)

    return delimiter.join(prepend + [line] + append)
