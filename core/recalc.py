"""Recalculate numeric column values: new_value = old_value * factor + offset."""

from collections.abc import Iterable, Iterator

from core.columns import parse_column_spec


def recalculate_columns(
    lines: Iterable[str],
    spec: str,
    factor: float,
    offset: float,
    delimiter: str = "\t",
    header_lines: int = 0,
) -> Iterator[str]:
    """Apply ``value * factor + offset`` to selected columns, pass the rest through.

    Column indices are resolved lazily from the first delimited data line.
    Non-numeric values are passed through unchanged.
    Lines without *delimiter* are always passed through unchanged.

    Args:
        lines:        Input line stream (trailing newlines already stripped).
        spec:         Column spec, e.g. ``"4"`` or ``"2,4"`` or ``"3-5"``. 1-based.
        factor:       Multiplicative factor applied first.
        offset:       Additive offset applied after multiplication.
        delimiter:    Field separator (default tab).
        header_lines: Number of leading lines to pass through unchanged.
    """
    col_set: set[int] | None = None
    for line_num, line in enumerate(lines, start=1):
        if line_num <= header_lines or delimiter not in line:
            yield line
            continue
        if col_set is None:
            total = len(line.split(delimiter))
            col_set = set(parse_column_spec(spec, total))
        parts = line.split(delimiter)
        out_parts: list[str] = []
        for i, part in enumerate(parts):
            if i in col_set:
                try:
                    val = float(part) * factor + offset
                    out_parts.append(f"{val:.15g}")
                except ValueError:
                    out_parts.append(part)
            else:
                out_parts.append(part)
        yield delimiter.join(out_parts)
