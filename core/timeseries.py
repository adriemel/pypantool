"""Time-series line thinning ("Extract 10 min lines").

Keeps a data line only when at least *interval_seconds* have elapsed since the
last kept line, based on an ISO-format date/time column located via the header.
Matches the original PanTool behaviour: the first and last data lines are
always written, and a malformed date/time cell produces an error-marker line
in place of the data line.
"""

from collections.abc import Iterable, Iterator
from datetime import datetime

FORMAT_ERROR_LINE = (
    "Format of date/time is wrong. Must be yyyy-MM-ddThh:mm, "
    "yyyy-MM-ddThh:mm:ss or yyyy-MM-ddThh:mm:ss.zzz"
)


def find_datetime_column(header: str, delimiter: str = "\t") -> int:
    """Return the 0-based index of the first header cell starting with
    ``date/time`` (case-insensitive), or -1 if none exists.
    """
    for idx, cell in enumerate(header.split(delimiter)):
        if cell.strip().lower().startswith("date/time"):
            return idx
    return -1


def extract_interval_lines(
    lines: Iterable[str],
    interval_seconds: int = 600,
    keep_header: bool = True,
    delimiter: str = "\t",
) -> Iterator[str]:
    """Thin a time series to one line per *interval_seconds*.

    The first line is treated as the header and must contain a column whose
    name starts with ``Date/Time``.  Data lines are kept when their timestamp
    is at least *interval_seconds* after the last kept timestamp.  The final
    data line is always written, matching the original PanTool.

    Args:
        lines:            Input line stream (without trailing newlines).
        interval_seconds: Minimum spacing between kept lines. Default 600 (10 min).
        keep_header:      When ``True``, the header line is written to the output.
        delimiter:        Column separator.

    Raises:
        ValueError: If the header has no ``Date/Time`` column or the interval
                    is not positive.
    """
    if interval_seconds <= 0:
        raise ValueError("Interval must be a positive number of seconds.")

    it = iter(lines)
    header = next(it, None)
    if header is None:
        return

    col = find_datetime_column(header, delimiter)
    if col < 0:
        raise ValueError("No 'Date/Time' column found in the header line.")

    if keep_header:
        yield header

    last_kept: datetime | None = None
    pending: str | None = None

    for line in it:
        if pending is not None:
            dt = _parse_iso(pending, col, delimiter)
            if dt is None:
                yield FORMAT_ERROR_LINE
            elif last_kept is None or (dt - last_kept).total_seconds() >= interval_seconds:
                last_kept = dt
                yield pending
        pending = line

    # The last data line is always written, without interval checking.
    if pending is not None:
        yield pending


def _parse_iso(line: str, col: int, delimiter: str) -> datetime | None:
    """Parse the date/time cell of *line*; return ``None`` when malformed."""
    cells = line.split(delimiter)
    if col >= len(cells):
        return None
    cell = cells[col].strip()
    if "T" not in cell:
        return None
    try:
        return datetime.fromisoformat(cell)
    except ValueError:
        return None
