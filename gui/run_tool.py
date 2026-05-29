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
from gui.worker import ConcatWorker, FilelistWorker, ProcessWorker


def run_tool(
    main_window,
    process_fn: Callable[[Iterable[str]], Iterator[str]],
    label: str,
) -> None:
    """Build jobs from *main_window*'s file list, create a worker, and start it.

    Args:
        main_window: The :class:`~gui.main_window.MainWindow` instance.
        process_fn:  Core function already bound with its parameters via
                     ``functools.partial``.  Signature must be
                     ``(Iterable[str]) -> Iterator[str]``.
        label:       Short human-readable operation name shown in the status bar.
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
) -> None:
    """Merge all loaded files into one output using a concat core function.

    Args:
        main_window: The :class:`~gui.main_window.MainWindow` instance.
        process_fn:  Concat function already bound with parameters via
                     ``functools.partial``.  Signature must be
                     ``(Iterable[tuple[str, Iterable[str]]]) -> Iterator[str]``.
        label:       Short operation name shown in the status bar.
    """
    in_paths = main_window.files
    if len(in_paths) < 2:
        QMessageBox.warning(main_window, label, "At least two files are required.")
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
