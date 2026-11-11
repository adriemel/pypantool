"""Recalculate numeric column values: new_value = old_value * factor + offset."""

import re
from collections.abc import Iterable, Iterator
from decimal import Decimal

from core.columns import parse_column_spec
from core.header import header_finder, is_comment

# Plain decimal numbers only: no "nan", "inf", "1_000" or decimal commas.
PLAIN_NUMBER = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?")


def recalculate_columns(
    lines: Iterable[str],
    spec: str,
    factor: float,
    offset: float,
    delimiter: str = "\t",
    header_lines: int = 0,
    header_line: int = 1,
    comment_prefix: str = "//",
) -> Iterator[str]:
    """Apply ``value * factor + offset`` to selected columns, pass the rest through.

    The arithmetic is exact decimal arithmetic, so the written precision
    follows the input: ``12.50 * 1`` stays ``12.50``, ``34.120 * 3`` gives
    ``102.360``, and long integers keep all digits.  Results are written in
    plain notation, never with an exponent.

    The column count comes from the header line (see :mod:`core.header`);
    lines before it pass through unchanged.  Cells that are not plain decimal
    numbers (text, empty, ``nan``, decimal commas) pass through unchanged, as
    do comment lines and lines without *delimiter*.

    Args:
        lines:          Input line stream (trailing newlines already stripped).
        spec:           Column spec, e.g. ``"4"`` or ``"2,4"`` or ``"3-5"``. 1-based.
        factor:         Multiplicative factor applied first.
        offset:         Additive offset applied after multiplication.
        delimiter:      Field separator (default tab).
        header_lines:   Number of leading lines to pass through unchanged.
        header_line:    Earliest 1-based line the header may be on.
        comment_prefix: Prefix of comment lines.

    Raises:
        ValueError: If *spec* is invalid for the header's column count.
    """
    dec_factor = _to_decimal(factor)
    dec_offset = _to_decimal(offset)
    is_header = header_finder(header_line, comment_prefix, delimiter)
    col_set: set[int] | None = None

    for line_num, line in enumerate(lines, start=1):
        if col_set is None:
            if not is_header(line_num, line):
                yield line
                continue
            col_set = set(parse_column_spec(spec, len(line.split(delimiter))))
        if (line_num <= header_lines or delimiter not in line
                or is_comment(line, comment_prefix)):
            yield line
            continue
        parts = line.split(delimiter)
        for i in col_set:
            if i < len(parts) and PLAIN_NUMBER.fullmatch(parts[i].strip()):
                value = Decimal(parts[i].strip()) * dec_factor + dec_offset
                parts[i] = format(value, "f")
        yield delimiter.join(parts)


def _to_decimal(value: float) -> Decimal:
    """Convert a user-entered number without adding digits (2.0 -> 2, 0.1 -> 0.1)."""
    as_float = float(value)
    if as_float.is_integer():
        return Decimal(int(as_float))
    return Decimal(repr(as_float))
