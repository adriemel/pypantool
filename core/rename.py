"""Filename transformation: search/replace, prepend, append."""

from pathlib import Path


def apply_rename(
    name: str,
    search: str = "",
    replace: str = "",
    prefix: str = "",
    suffix: str = "",
) -> str:
    """Return the transformed filename.

    Operations are applied in order: search/replace → prefix → suffix.

    Args:
        name:    Original filename, e.g. ``"data.tab"``.
        search:  Substring to find in the full filename.
        replace: Replacement for every occurrence of *search*.
        prefix:  Text prepended to the full filename.
        suffix:  Text inserted after the stem but before the extension,
                 e.g. ``"_v2"`` turns ``"data.tab"`` into ``"data_v2.tab"``.
    """
    result = name
    if search:
        result = result.replace(search, replace)
    if prefix:
        result = prefix + result
    if suffix:
        p = Path(result)
        result = p.stem + suffix + p.suffix
    return result


def preview_renames(
    paths: list[Path],
    search: str = "",
    replace: str = "",
    prefix: str = "",
    suffix: str = "",
) -> list[tuple[Path, Path]]:
    """Return ``(old_path, new_path)`` pairs without modifying the filesystem."""
    return [
        (path, path.parent / apply_rename(path.name, search=search, replace=replace, prefix=prefix, suffix=suffix))
        for path in paths
    ]


_FORBIDDEN = '<>:"/\\|?*'


def rename_problem(pairs: list[tuple[Path, Path]]) -> str | None:
    """Return why *pairs* cannot be renamed safely, or ``None`` if they can.

    Checks for empty or invalid new names, two files mapped to the same
    name, and targets that already exist on disk.

    Args:
        pairs: ``(old_path, new_path)`` pairs from :func:`preview_renames`.
    """
    changed = [(old, new) for old, new in pairs if old != new]
    sources = {str(old).lower() for old, _ in changed}
    seen: set[str] = set()
    for old, new in pairs:
        key = str(new).lower()
        if key in seen:
            return f"Several files would be named {new.name}."
        seen.add(key)
    for old, new in changed:
        if new == old.parent or not Path(new.name).stem.strip():
            return f"{old.name} would get an empty name."
        bad = sorted(set(new.name) & set(_FORBIDDEN))
        if bad:
            return f"{new.name} contains characters not allowed in file names: {' '.join(bad)}"
        if new.exists() and str(new).lower() not in sources:
            return f"{new.name} already exists in the folder."
    return None
