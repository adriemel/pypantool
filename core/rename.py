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
