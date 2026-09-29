"""Output filename pattern resolution.

Supported tokens:
  %N  — input filename without extension
  %E  — input file extension, including the leading dot (e.g. '.txt')
  %a  — auto-incrementing run counter (1, 2, 3 …)
"""

import os
from collections.abc import Callable
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


def same_file(a: Path, b: Path) -> bool:
    """True if *a* and *b* are the same file (case-insensitive on Windows,
    hard links included)."""
    if _key(a) == _key(b):
        return True
    id_a = _file_id(a)
    return id_a is not None and id_a == _file_id(b)


def input_matcher(in_paths: list[Path]) -> Callable[[Path], bool]:
    """Return a fast predicate: is a path one of *in_paths* (see :func:`same_file`)?"""
    in_keys = {_key(p) for p in in_paths}
    in_ids = {_file_id(p) for p in in_paths} - {None}

    def is_input(path: Path) -> bool:
        return _key(path) in in_keys or _file_id(path) in in_ids

    return is_input


def output_problem(in_paths: list[Path], out_paths: list[Path]) -> str | None:
    """Return an error message if an output would overwrite an input or two
    outputs share a name; ``None`` if it is safe to run.

    Args:
        in_paths:  Files that will be read.
        out_paths: Files that will be written.
    """
    is_input = input_matcher(in_paths)
    for out in out_paths:
        if is_input(out):
            return (
                f"Output file {out.name} would overwrite an input file. "
                "Change the output name pattern in File › Options."
            )
    if len({_key(o) for o in out_paths}) < len(out_paths):
        return (
            "Several input files map to the same output file name. "
            "Include %N in the output name pattern in File › Options."
        )
    return None


def _key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(path))


def _file_id(path: Path) -> tuple[int, int] | None:
    try:
        st = path.stat()
    except OSError:
        return None
    return (st.st_dev, st.st_ino)
