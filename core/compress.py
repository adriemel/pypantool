"""Compress and decompress files and folders using the Python stdlib.

All operations stream in fixed-size chunks — archive members are never read
into memory as a whole.  Archives are created next to their source; existing
targets are overwritten.

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
    """
    suffix = path.suffix.lower()
    target_dir = path.parent

    if suffix == ".zip":
        with zipfile.ZipFile(path) as zf:
            zf.extractall(target_dir)
            return [target_dir / name for name in zf.namelist()
                    if not name.endswith("/")]

    if suffix in (".tar", ".tgz") or path.name.lower().endswith(".tar.gz"):
        with tarfile.open(path) as tf:
            tf.extractall(target_dir, filter="data")
            return [target_dir / m.name for m in tf.getmembers() if m.isfile()]

    if suffix == ".gz":
        out = path.with_name(path.name[: -len(".gz")])
        with gzip.open(path, "rb") as fh_in, open(out, "wb") as fh_out:
            shutil.copyfileobj(fh_in, fh_out, _CHUNK)
        return [out]

    raise ValueError(f"Unsupported archive type: {path.name}")
