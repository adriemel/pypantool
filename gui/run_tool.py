"""Shared helper that wires a core processing function to the GUI.

Usage in a dialog::

    from functools import partial
    from core.lines import extract_lines
    from gui.run_tool import run_tool

    run_tool(self._mw, partial(extract_lines, spec="1-3"), "Extract lines")
"""

from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from core.naming import resolve_output_path
from gui.worker import (
    ConcatWorker,
    FilelistWorker,
    ProcessWorker,
    RenameWorker,
    SplitWorker,
)


def run_tool(
    main_window,
    process_fn: Callable[[Iterable[str]], Iterator[str]],
    label: str,
    pass_path: bool = False,
) -> None:
    """Build jobs from *main_window*'s file list, create a worker, and start it.

    Args:
        main_window: The :class:`~gui.main_window.MainWindow` instance.
        process_fn:  Core function already bound with its parameters via
                     ``functools.partial``.  Signature must be
                     ``(Iterable[str]) -> Iterator[str]``.
        label:       Short human-readable operation name shown in the status bar.
        pass_path:   Forwarded to :class:`~gui.worker.ProcessWorker`; when
                     ``True`` the core function also receives the input path.
    """
    settings = main_window.current_settings()
    counter = main_window.run_counter

    jobs: list[tuple[Path, Path]] = [
        (path, resolve_output_path(settings["pattern"], path, counter))
        for path in main_window.files
    ]
    out_paths = [out for _, out in jobs]

    worker = ProcessWorker(
        jobs=jobs,
        process_fn=process_fn,
        in_encoding=settings["in_encoding"],
        out_encoding=settings["out_encoding"],
        pass_path=pass_path,
    )

    def _on_file_started(idx: int, total: int, name: str) -> None:
        main_window.set_busy(f"{label}: {name} ({idx}/{total})")

    def _on_error(msg: str) -> None:
        main_window.set_idle()
        QMessageBox.warning(main_window, "Error", msg)

    def _on_done() -> None:
        main_window.increment_run_counter()
        main_window.replace_files(out_paths)
        main_window.set_idle(f"Done — {len(out_paths)} file(s) written")

    worker.file_started.connect(_on_file_started)
    worker.error.connect(_on_error)
    worker.all_done.connect(_on_done)

    main_window.attach_worker(worker)


def run_concat(
    main_window,
    process_fn: Callable[[Iterable[tuple[str, Iterable[str]]]], Iterator[str]],
    label: str,
    min_files: int = 2,
) -> None:
    """Merge all loaded files into one output using a concat core function.

    Args:
        main_window: The :class:`~gui.main_window.MainWindow` instance.
        process_fn:  Concat function already bound with parameters via
                     ``functools.partial``.  Signature must be
                     ``(Iterable[tuple[str, Iterable[str]]]) -> Iterator[str]``.
        label:       Short operation name shown in the status bar.
        min_files:   Minimum number of loaded files required (2 for true
                     concatenation, 1 for report tools like Search One String).
    """
    in_paths = main_window.files
    if len(in_paths) < min_files:
        QMessageBox.warning(
            main_window, label,
            f"At least {min_files} file(s) are required.",
        )
        return

    settings = main_window.current_settings()
    out_path = resolve_output_path(settings["pattern"], in_paths[0], main_window.run_counter)

    worker = ConcatWorker(
        in_paths=in_paths,
        out_path=out_path,
        process_fn=process_fn,
        in_encoding=settings["in_encoding"],
        out_encoding=settings["out_encoding"],
    )

    def _on_error(msg: str) -> None:
        main_window.set_idle()
        QMessageBox.warning(main_window, "Error", msg)

    def _on_done(path: Path) -> None:
        main_window.increment_run_counter()
        main_window.replace_files([path])
        main_window.set_idle("Done — 1 file written")

    main_window.set_busy(label)
    worker.error.connect(_on_error)
    worker.done.connect(_on_done)

    main_window.attach_worker(worker)


def run_split(
    main_window,
    process_fn: Callable[[Iterable[str]], Iterator[tuple[int, str]]],
    label: str,
    sequential: bool = True,
) -> None:
    """Split every loaded file into numbered chunk files.

    Args:
        main_window: The :class:`~gui.main_window.MainWindow` instance.
        process_fn:  Split function already bound with parameters via
                     ``functools.partial``.  Signature must be
                     ``(Iterable[str]) -> Iterator[tuple[int, str]]``.
        label:       Short operation name shown in the status bar.
        sequential:  ``True`` when chunk indices are monotonic (line splits);
                     ``False`` when chunks interleave (column splits).
    """
    settings = main_window.current_settings()

    worker = SplitWorker(
        in_paths=main_window.files,
        process_fn=process_fn,
        sequential=sequential,
        in_encoding=settings["in_encoding"],
        out_encoding=settings["out_encoding"],
    )

    def _on_file_started(idx: int, total: int, name: str) -> None:
        main_window.set_busy(f"{label}: {name} ({idx}/{total})")

    def _on_error(msg: str) -> None:
        main_window.set_idle()
        QMessageBox.warning(main_window, "Error", msg)

    def _on_done(created: list) -> None:
        main_window.increment_run_counter()
        main_window.replace_files(created)
        main_window.set_idle(f"Done — {len(created)} file(s) written")

    worker.file_started.connect(_on_file_started)
    worker.error.connect(_on_error)
    worker.all_done.connect(_on_done)

    main_window.attach_worker(worker)


def run_rename(
    main_window,
    search: str = "",
    replace: str = "",
    prefix: str = "",
    suffix: str = "",
) -> None:
    """Rename all loaded files in place and update the file list.

    Args:
        main_window: The :class:`~gui.main_window.MainWindow` instance.
        search:  Substring to find in the filename.
        replace: Replacement for every occurrence of *search*.
        prefix:  Text prepended to the full filename.
        suffix:  Text inserted after the stem, before the extension.
    """
    from core.rename import preview_renames

    pairs = preview_renames(
        main_window.files,
        search=search,
        replace=replace,
        prefix=prefix,
        suffix=suffix,
    )

    worker = RenameWorker(pairs=pairs)

    def _on_file_renamed(idx: int, total: int, old_name: str, new_path: Path) -> None:
        main_window.set_busy(f"Rename: {old_name} → {new_path.name} ({idx}/{total})")

    def _on_error(msg: str) -> None:
        main_window.set_idle()
        QMessageBox.warning(main_window, "Rename error", msg)

    def _on_done(new_paths: list) -> None:
        main_window.replace_files(new_paths)
        main_window.set_idle(f"Done — {len(new_paths)} file(s) renamed")

    main_window.set_busy("Renaming files…")
    worker.file_renamed.connect(_on_file_renamed)
    worker.error.connect(_on_error)
    worker.all_done.connect(_on_done)

    main_window.attach_worker(worker)


def run_filelist(main_window) -> None:
    """Export metadata for all loaded files to a single output file.

    Args:
        main_window: The :class:`~gui.main_window.MainWindow` instance.
    """
    from functools import partial

    from core.filelist import emit_filelist

    in_paths = main_window.files
    settings = main_window.current_settings()
    out_path = resolve_output_path(settings["pattern"], in_paths[0], main_window.run_counter)
    delimiter = settings.get("delimiter", "\t")

    worker = FilelistWorker(
        in_paths=in_paths,
        out_path=out_path,
        process_fn=partial(emit_filelist, delimiter=delimiter),
        out_encoding=settings["out_encoding"],
    )

    def _on_error(msg: str) -> None:
        main_window.set_idle()
        QMessageBox.warning(main_window, "Error", msg)

    def _on_done(path: Path) -> None:
        main_window.increment_run_counter()
        main_window.replace_files([path])
        main_window.set_idle("Done — 1 file written")

    main_window.set_busy("Save file list")
    worker.error.connect(_on_error)
    worker.done.connect(_on_done)

    main_window.attach_worker(worker)
