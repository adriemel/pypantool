"""Time-series line thinning ("Extract 10 min lines").

Keeps a data line only when at least *interval_seconds* have elapsed since the
last kept line, based on an ISO-format date/time column located via the header.
Matches the original PanTool behaviour: the first and last data lines are
always written, and a malformed date/time cell produces an error-marker line
in place of the data line.
"""

from collections.abc import Iterable, Iterator
from datetime import datetime

from core.header import header_finder

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
    header_line: int = 1,
    comment_prefix: str = "//",
) -> Iterator[str]:
    """Thin a time series to one line per *interval_seconds*.

    The header line (see :mod:`core.header`) must contain a column whose name
    starts with ``Date/Time``.  Data lines are kept when their timestamp is at
    least *interval_seconds* after the last kept timestamp.  The final data
    line is always written, matching the original PanTool.

    Args:
        lines:            Input line stream (without trailing newlines).
        interval_seconds: Minimum spacing between kept lines. Default 600 (10 min).
        keep_header:      When ``True``, the header line and any lines before
                          it are written to the output.
        delimiter:        Column separator.
        header_line:      Earliest 1-based line the header may be on.
        comment_prefix:   Prefix of comment lines.

    Raises:
        ValueError: If the header has no ``Date/Time`` column, the interval
                    is not positive, or timestamps with and without a UTC
                    offset are mixed.
    """
    if interval_seconds <= 0:
        raise ValueError("Interval must be a positive number of seconds.")

    is_header = header_finder(header_line, comment_prefix, delimiter,
                              require_delimiter=False)
    col = -1
    seen_any = False
    last_kept: datetime | None = None
    pending: str | None = None
    pending_no = 0

    for lineno, line in enumerate(lines, start=1):
        seen_any = True
        if col < 0:
            if is_header(lineno, line):
                col = find_datetime_column(line, delimiter)
                if col < 0:
                    raise ValueError("No 'Date/Time' column found in the header line.")
            if keep_header:
                yield line
            continue

        if pending is not None:
            dt = _parse_iso(pending, col, delimiter)
            if dt is None:
                yield FORMAT_ERROR_LINE
            elif last_kept is None or _seconds(last_kept, dt, pending_no) >= interval_seconds:
                last_kept = dt
                yield pending
        pending, pending_no = line, lineno

    if seen_any and col < 0:
        raise ValueError("No 'Date/Time' column found in the header line.")

    # The last data line is always written, without interval checking.
    if pending is not None:
        yield pending


def _seconds(earlier: datetime, later: datetime, lineno: int) -> float:
    try:
        return (later - earlier).total_seconds()
    except TypeError:
        raise ValueError(
            f"Line {lineno}: timestamps with and without a UTC offset are "
            "mixed in the Date/Time column."
        ) from None


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
