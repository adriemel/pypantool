"""Convert a date/time column to ISO 8601 (``yyyy-MM-ddTHH:mm:ss``).

The input format is described with PanTool/Qt-style tokens:

==========  ==============================================================
``yyyy``    4-digit year            ``yy``   2-digit year (00-68 = 20xx)
``MM``      2-digit month           ``M``    month, 1 or 2 digits
``MMM``     English month abbreviation (Jan, Feb, ...; case-insensitive)
``dd``      2-digit day             ``d``    day, 1 or 2 digits
``DDD``     day of year, 1 to 3 digits (use instead of month and day)
``HH``      2-digit hour (``hh`` is the same)   ``H``/``h``  1 or 2 digits
``mm``      2-digit minute          ``m``    minute, 1 or 2 digits
``ss``      2-digit second          ``s``    second, 1 or 2 digits
``zzz``     fraction of a second, 1 to 6 digits
``AP``      AM/PM marker (hours are then read as 12-hour clock)
==========  ==============================================================

Any other character must appear literally; a space matches one or more
whitespace characters; text in single quotes is literal (``HH'h'mm``).
Two special formats exist: ``excel`` (serial day number, 1900 date system)
and ``unix`` (seconds since 1970-01-01T00:00:00).

The written precision follows the format: date only, minutes, seconds, or
milliseconds.  ``excel`` and ``unix`` values are rounded to whole seconds.
"""

import re
from collections.abc import Callable, Iterable, Iterator
from datetime import datetime, timedelta

from core.header import header_finder, is_comment
from core.recalc import PLAIN_NUMBER

HEADER_NAME = "Date/Time"
# Stop when this many values in a row at the start of a file cannot be read.
ABORT_AFTER_FAILURES = 100

_MONTHS = {m: i for i, m in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}

# token -> (group name, regex); longest tokens first.
_TOKENS: list[tuple[str, str, str]] = [
    ("yyyy", "year", r"\d{4}"), ("yy", "year2", r"\d{2}"),
    ("MMM", "monname", r"[A-Za-z]{3}"), ("MM", "month", r"\d{2}"), ("M", "month", r"\d{1,2}"),
    ("DDD", "doy", r"\d{1,3}"), ("dd", "day", r"\d{2}"), ("d", "day", r"\d{1,2}"),
    ("HH", "hour", r"\d{2}"), ("hh", "hour", r"\d{2}"),
    ("H", "hour", r"\d{1,2}"), ("h", "hour", r"\d{1,2}"),
    ("mm", "minute", r"\d{2}"), ("m", "minute", r"\d{1,2}"),
    ("ss", "second", r"\d{2}"), ("s", "second", r"\d{1,2}"),
    ("zzz", "frac", r"\d{1,6}"), ("AP", "ampm", r"[AaPp]\.?[Mm]\.?"), ("ap", "ampm", r"[AaPp]\.?[Mm]\.?"),
]

_EXCEL_EPOCH = datetime(1899, 12, 30)
_UNIX_EPOCH = datetime(1970, 1, 1)


def make_parser(in_format: str) -> tuple[Callable[[str], datetime | None], str]:
    """Compile *in_format* into a parser.

    Args:
        in_format: Token pattern, ``"excel"`` or ``"unix"`` (see module docstring).

    Returns:
        ``(parse, precision)``: *parse* maps a cell text to a ``datetime`` or
        ``None`` when it does not match; *precision* is ``"date"``,
        ``"minute"``, ``"second"`` or ``"milli"``.

    Raises:
        ValueError: If the format is empty, repeats a token, or lacks a year
                    or a day (month + day, or day of year).
    """
    fmt = in_format.strip()
    if not fmt:
        raise ValueError("Date/time format must not be empty.")
    if fmt.lower() in ("excel", "unix"):
        return _serial_parser(fmt.lower()), "second"

    pattern, groups = _compile(fmt)
    if not groups & {"year", "year2"}:
        raise ValueError("The format needs a year (yyyy or yy).")
    if "doy" not in groups and not ({"day"} <= groups and groups & {"month", "monname"}):
        raise ValueError("The format needs month and day (MM, dd) or a day of year (DDD).")
    if groups & {"minute", "second", "frac", "ampm"} and "hour" not in groups:
        raise ValueError("The format has minutes or seconds but no hour (HH).")
    rx = re.compile(pattern)

    def parse(text: str) -> datetime | None:
        m = rx.fullmatch(text.strip())
        if m is None:
            return None
        g = m.groupdict()
        try:
            return _build(g)
        except (ValueError, KeyError):
            return None

    if "frac" in groups:
        precision = "milli"
    elif "second" in groups:
        precision = "second"
    elif "hour" in groups:
        precision = "minute"
    else:
        precision = "date"
    return parse, precision


def _compile(fmt: str) -> tuple[str, set[str]]:
    parts: list[str] = []
    groups: set[str] = set()
    i = 0
    while i < len(fmt):
        ch = fmt[i]
        if ch == "'":
            end = fmt.find("'", i + 1)
            if end < 0:
                raise ValueError("Unclosed quote in the date/time format.")
            parts.append(re.escape(fmt[i + 1:end]))
            i = end + 1
            continue
        for token, group, rx in _TOKENS:
            if fmt.startswith(token, i):
                if group in groups:
                    raise ValueError(f"The format contains {token!r} (or its variant) twice.")
                groups.add(group)
                parts.append(f"(?P<{group}>{rx})")
                i += len(token)
                break
        else:
            parts.append(r"\s+" if ch.isspace() else re.escape(ch))
            i += 1
    return "".join(parts), groups


def _build(g: dict[str, str | None]) -> datetime:
    if g.get("year") is not None:
        year = int(g["year"])
    else:
        short = int(g["year2"])
        year = 2000 + short if short <= 68 else 1900 + short
    hour = int(g.get("hour") or 0)
    if g.get("ampm") is not None:
        if not 1 <= hour <= 12:
            raise ValueError("hour out of range for AM/PM")
        hour = hour % 12 + (12 if g["ampm"][0] in "Pp" else 0)
    micro = int((g.get("frac") or "0").ljust(6, "0"))
    minute, second = int(g.get("minute") or 0), int(g.get("second") or 0)
    if g.get("doy") is not None:
        base = datetime(year, 1, 1, hour, minute, second, micro)
        stamp = base + timedelta(days=int(g["doy"]) - 1)
        if int(g["doy"]) < 1 or stamp.year != year:
            raise ValueError("day of year out of range")
        return stamp
    month = _MONTHS[g["monname"].lower()] if g.get("monname") is not None else int(g["month"])
    return datetime(year, month, int(g["day"]), hour, minute, second, micro)


def _serial_parser(kind: str) -> Callable[[str], datetime | None]:
    def parse(text: str) -> datetime | None:
        text = text.strip()
        if not PLAIN_NUMBER.fullmatch(text):
            return None
        try:
            if kind == "excel":
                return _EXCEL_EPOCH + timedelta(seconds=round(float(text) * 86400))
            return _UNIX_EPOCH + timedelta(seconds=round(float(text)))
        except (OverflowError, ValueError):
            return None
    return parse


def format_iso(stamp: datetime, precision: str) -> str:
    """Format *stamp* as ISO 8601 with the given precision (see :func:`make_parser`)."""
    text = f"{stamp.year:04d}-{stamp.month:02d}-{stamp.day:02d}"
    if precision == "date":
        return text
    text += f"T{stamp.hour:02d}:{stamp.minute:02d}"
    if precision == "minute":
        return text
    text += f":{stamp.second:02d}"
    if precision == "milli":
        text += f".{stamp.microsecond // 1000:03d}"
    return text


def convert_datetime(
    lines: Iterable[str],
    date_column: int,
    in_format: str,
    time_column: int = 0,
    utc_offset_hours: float = 0.0,
    keep_original: bool = False,
    on_fail: Callable[[int, str], None] | None = None,
    delimiter: str = "\t",
    header_line: int = 1,
    comment_prefix: str = "//",
) -> Iterator[str]:
    """Rewrite a date/time column as ISO 8601.

    The header cell becomes ``Date/Time``.  Lines before the header, comment
    lines, empty lines and lines without *delimiter* pass through unchanged.
    Empty cells stay empty.  Cells that do not match *in_format* are left as
    they are and reported through *on_fail*.

    Args:
        lines:            Input line stream (without trailing newlines).
        date_column:      1-based number of the column to convert.
        in_format:        Format of the input values (see module docstring).
        time_column:      Optional 1-based number of a separate time column
                          (0 = none).  Date and time are joined with one
                          space before parsing, so *in_format* must describe
                          ``"<date> <time>"``.
        utc_offset_hours: Offset of the input times from UTC (e.g. ``2`` for
                          UTC+2); it is subtracted so the output is UTC.
        keep_original:    ``False``: the date column is replaced and the time
                          column removed.  ``True``: a new ``Date/Time``
                          column is inserted before the date column and the
                          original columns stay.
        on_fail:          Called with ``(1-based line number, cell text)``
                          for every cell that could not be converted.
        delimiter:        Column separator.
        header_line:      Earliest 1-based line the header may be on.
        comment_prefix:   Prefix of comment lines.

    Raises:
        ValueError: If the format or a column number is invalid, a UTC offset
                    is given for a date-only format, or none of the first
                    ``ABORT_AFTER_FAILURES`` values matches the format.
    """
    parse, precision = make_parser(in_format)
    if date_column < 1:
        raise ValueError("Date column must be 1 or greater.")
    if time_column < 0 or time_column == date_column:
        raise ValueError("Time column must be a different column (or 0 for none).")
    if utc_offset_hours and precision == "date":
        raise ValueError("A UTC offset needs a format that contains the time.")
    shift = timedelta(hours=utc_offset_hours)
    d, t = date_column - 1, time_column - 1
    need = max(date_column, time_column)

    is_header = header_finder(header_line, comment_prefix, delimiter,
                              require_delimiter=False)
    header_found = False
    converted = 0
    failed = 0

    for lineno, line in enumerate(lines, start=1):
        if not header_found:
            if not is_header(lineno, line):
                yield line
                continue
            header_found = True
            cells = line.split(delimiter)
            if len(cells) < need:
                raise ValueError(
                    f"Column {need} does not exist: the header line has "
                    f"{len(cells)} column(s)."
                )
            yield delimiter.join(_place(cells, HEADER_NAME, d, t, keep_original))
            continue
        if line == "" or is_comment(line, comment_prefix):
            yield line
            continue
        cells = line.split(delimiter)
        if len(cells) < need:
            yield line
            continue

        text = cells[d].strip() if t < 0 else f"{cells[d].strip()} {cells[t].strip()}".strip()
        if not text:
            new = ""
        else:
            stamp = parse(text)
            if stamp is None:
                failed += 1
                if on_fail is not None:
                    on_fail(lineno, text)
                if not converted and failed >= ABORT_AFTER_FAILURES:
                    raise ValueError(
                        f"None of the first {failed} values matches the format "
                        f"{in_format!r} (first value on line {lineno - failed + 1} "
                        f"or later, e.g. {text!r})."
                    )
                new = "" if keep_original else text
            else:
                converted += 1
                new = format_iso(stamp - shift, precision)
        yield delimiter.join(_place(cells, new, d, t, keep_original))


def _place(cells: list[str], value: str, d: int, t: int, keep_original: bool) -> list[str]:
    """Put *value* into the row: insert before the date cell, or replace it
    and drop the time cell."""
    if keep_original:
        return cells[:d] + [value] + cells[d:]
    cells[d] = value
    if t >= 0:
        del cells[t]
    return cells
