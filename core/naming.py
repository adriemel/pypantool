"""Output filename pattern resolution.

Supported tokens:
  %N  — input filename without extension
  %E  — input file extension, including the leading dot (e.g. '.txt')
  %a  — auto-incrementing run counter (1, 2, 3 …)
"""

from pathlib import Path


def resolve_output_name(pattern: str, input_path: Path, counter: int) -> str:
    """Return an output filename string from *pattern* and the given inputs.

    Args:
        pattern:    User-configured pattern, e.g. ``"%N_out%E"`` or ``"%N_%a.txt"``.
        input_path: Path to the source file being processed.
        counter:    Current run counter for ``%a`` substitution (1-based).

    Returns:
        A plain filename string (no directory component).
    """
    stem = input_path.stem
    ext = input_path.suffix  # includes the dot, e.g. '.txt'; empty string if none

    result = pattern
    result = result.replace("%N", stem)
    result = result.replace("%E", ext)
    result = result.replace("%a", str(counter))
    return result


def resolve_output_path(pattern: str, input_path: Path, counter: int) -> Path:
    """Return the full output :class:`~pathlib.Path` next to *input_path*.

    The output file is placed in the same directory as the input file.
    """
    name = resolve_output_name(pattern, input_path, counter)
    return input_path.parent / name


def unique_path(directory: Path, stem: str, ext: str) -> Path:
    """Return ``directory/stem+ext``, or the first free ``stem_2+ext``, ``stem_3+ext`` …

    Never returns the path of an existing file.
    """
    candidate = directory / f"{stem}{ext}"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{stem}_{counter}{ext}"
        counter += 1
    return candidate
