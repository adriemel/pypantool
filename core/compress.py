"""Compress and decompress files and folders using the Python stdlib.

All operations stream in fixed-size chunks — archive members are never read
into memory as a whole.  Archives are created next to their source; an
existing archive of the same name is overwritten.  Decompression never
overwrites: it stops before extracting if a target file already exists.

``compress_file_zip``    — ``data.tab``  → ``data.tab.zip`` (single member)
``compress_file_gzip``   — ``data.tab``  → ``data.tab.gz``
``compress_folder_zip``  — ``folder/``   → ``folder.zip`` (recursive)
``compress_folder_targz``— ``folder/``   → ``folder.tar.gz`` (recursive)
``decompress_file``      — dispatches on ``.zip`` / ``.gz`` / ``.tar``
"""

import gzip
import shutil
import tarfile
import zipfile
from pathlib import Path

_CHUNK = 1024 * 1024  # 1 MiB


def compress_file_zip(path: Path) -> Path:
    """Compress a single file into ``<name>.zip`` next to it.

    Args:
        path: File to compress.

    Returns:
        Path of the created archive.
    """
    out = path.with_name(path.name + ".zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(path, arcname=path.name)
    return out


def compress_file_gzip(path: Path) -> Path:
    """Compress a single file into ``<name>.gz`` next to it.

    Args:
        path: File to compress.

    Returns:
        Path of the created archive.
    """
    out = path.with_name(path.name + ".gz")
    with open(path, "rb") as fh_in, gzip.open(out, "wb") as fh_out:
        shutil.copyfileobj(fh_in, fh_out, _CHUNK)
    return out


def compress_folder_zip(folder: Path) -> Path:
    """Zip a folder recursively into ``<folder>.zip`` next to it.

    Args:
        folder: Directory to compress.

    Returns:
        Path of the created archive.

    Raises:
        ValueError: If *folder* is not a directory.
    """
    if not folder.is_dir():
        raise ValueError(f"Not a folder: {folder}")
    out = folder.with_name(folder.name + ".zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for member in sorted(folder.rglob("*")):
            if member.is_file() and member != out:
                zf.write(member, arcname=member.relative_to(folder.parent))
    return out


def compress_folder_targz(folder: Path) -> Path:
    """Pack a folder recursively into ``<folder>.tar.gz`` next to it.

    Args:
        folder: Directory to compress.

    Returns:
        Path of the created archive.

    Raises:
        ValueError: If *folder* is not a directory.
    """
    if not folder.is_dir():
        raise ValueError(f"Not a folder: {folder}")
    out = folder.with_name(folder.name + ".tar.gz")
    with tarfile.open(out, "w:gz") as tf:
        tf.add(folder, arcname=folder.name)
    return out


def decompress_file(path: Path) -> list[Path]:
    """Decompress an archive next to itself, dispatching on the extension.

    ``.zip`` and ``.tar``/``.tar.gz``/``.tgz`` archives are extracted into the
    archive's directory; ``.gz`` files are unpacked to the same name without
    the suffix.

    Args:
        path: Archive to decompress.

    Returns:
        List of extracted file paths.

    Raises:
        ValueError: If the extension is not ``.zip``, ``.gz``, ``.tgz``
                    or ``.tar``.
        FileExistsError: If a file to be extracted already exists.
    """
    suffix = path.suffix.lower()
    target_dir = path.parent

    if suffix == ".zip":
        with zipfile.ZipFile(path) as zf:
            targets = [target_dir / name for name in zf.namelist()
                       if not name.endswith("/")]
            _refuse_existing(targets)
            zf.extractall(target_dir)
            return targets

    if suffix in (".tar", ".tgz") or path.name.lower().endswith(".tar.gz"):
        with tarfile.open(path) as tf:
            targets = [target_dir / m.name for m in tf.getmembers() if m.isfile()]
            _refuse_existing(targets)
            tf.extractall(target_dir, filter="data")
            return targets

    if suffix == ".gz":
        out = path.with_name(path.name[: -len(".gz")])
        _refuse_existing([out])
        with gzip.open(path, "rb") as fh_in, open(out, "wb") as fh_out:
            shutil.copyfileobj(fh_in, fh_out, _CHUNK)
        return [out]

    raise ValueError(f"Unsupported archive type: {path.name}")


def _refuse_existing(targets: list[Path]) -> None:
    existing = [t for t in targets if t.exists()]
    if existing:
        names = ", ".join(t.name for t in existing[:5])
        more = f" and {len(existing) - 5} more" if len(existing) > 5 else ""
        raise FileExistsError(
            f"would overwrite existing file(s): {names}{more}. "
            "Nothing was extracted."
        )
