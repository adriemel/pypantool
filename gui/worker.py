"""Background worker threads for file processing.

``ProcessWorker``   — one output per input file (standard tools).
``ConcatWorker``    — all input files merged into one output file.
``FilelistWorker``  — emit file metadata to one output file (no file reading).
"""

import contextlib
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal


class ProcessWorker(QThread):
    """Run a streaming core function over one or more files in a background thread.

    Signals:
        file_started(int, int, str):
            Emitted when a new file begins processing.
            Args: (1-based file index, total files, file name)
        line_progress(int):
            Emitted every N lines with the current line count.
        file_done(int, Path):
            Emitted when a file finishes.
            Args: (1-based file index, output path)
        all_done():
            Emitted when all files have been processed.
        error(str):
            Emitted if an exception occurs; processing stops.
    """

    file_started = Signal(int, int, str)
    line_progress = Signal(int)
    file_done = Signal(int, Path)
    all_done = Signal()
    error = Signal(str)

    # Emit a progress signal every this many lines to avoid flooding the GUI.
    PROGRESS_INTERVAL = 5_000

    def __init__(
        self,
        jobs: list[tuple[Path, Path]],
        process_fn: Callable[[Iterable[str]], Iterator[str]],
        in_encoding: str = "UTF-8",
        out_encoding: str = "UTF-8",
        parent: Any = None,
    ) -> None:
        """
        Args:
            jobs:        List of ``(input_path, output_path)`` pairs.
            process_fn:  Core function ``(Iterable[str]) -> Iterator[str]``.
                         May accept additional keyword arguments — bind them
                         with ``functools.partial`` before passing here.
            in_encoding: Encoding used to open input files.
            out_encoding: Encoding used to write output files.
        """
        super().__init__(parent)
        self._jobs = jobs
        self._process_fn = process_fn
        self._in_encoding = in_encoding
        self._out_encoding = out_encoding

    # ── QThread entry point ───────────────────────────────────────────────────

    def run(self) -> None:
        total = len(self._jobs)
        for idx, (in_path, out_path) in enumerate(self._jobs, start=1):
            self.file_started.emit(idx, total, in_path.name)
            try:
                self._process_one(in_path, out_path)
            except Exception as exc:  # noqa: BLE001
                self.error.emit(f"{in_path.name}: {exc}")
                return
            self.file_done.emit(idx, out_path)
        self.all_done.emit()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _process_one(self, in_path: Path, out_path: Path) -> None:
        line_count = 0
        with (
            open(in_path, encoding=self._in_encoding, errors="replace") as fh_in,
            open(out_path, "w", encoding=self._out_encoding, newline="") as fh_out,
        ):
            for out_line in self._process_fn(_stripped_lines(fh_in)):
                fh_out.write(out_line + "\n")
                line_count += 1
                if line_count % self.PROGRESS_INTERVAL == 0:
                    self.line_progress.emit(line_count)
        # Final progress tick so the GUI always reaches the real line count.
        self.line_progress.emit(line_count)


class ConcatWorker(QThread):
    """Merge N input files into one output file in a background thread.

    The *process_fn* receives an iterable of ``(filename, line_stream)`` pairs
    and returns an ``Iterator[str]``.  All input files are held open
    simultaneously so the function can interleave reads (needed for
    concat-by-columns).

    Signals:
        line_progress(int): Lines written so far (every PROGRESS_INTERVAL).
        done(Path):         Output path when finished successfully.
        error(str):         Error message; processing stopped.
    """

    line_progress = Signal(int)
    done = Signal(Path)
    error = Signal(str)

    PROGRESS_INTERVAL = 5_000

    def __init__(
        self,
        in_paths: list[Path],
        out_path: Path,
        process_fn: Callable[[Iterable[tuple[str, Iterable[str]]]], Iterator[str]],
        in_encoding: str = "UTF-8",
        out_encoding: str = "UTF-8",
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._in_paths = in_paths
        self._out_path = out_path
        self._process_fn = process_fn
        self._in_encoding = in_encoding
        self._out_encoding = out_encoding

    def run(self) -> None:
        try:
            with contextlib.ExitStack() as stack:
                handles = [
                    stack.enter_context(
                        open(p, encoding=self._in_encoding, errors="replace")
                    )
                    for p in self._in_paths
                ]
                inputs = [
                    (p.name, _stripped_lines(fh))
                    for p, fh in zip(self._in_paths, handles)
                ]
                line_count = 0
                with open(
                    self._out_path, "w", encoding=self._out_encoding, newline=""
                ) as fh_out:
                    for out_line in self._process_fn(inputs):
                        fh_out.write(out_line + "\n")
                        line_count += 1
                        if line_count % self.PROGRESS_INTERVAL == 0:
                            self.line_progress.emit(line_count)
            self.line_progress.emit(line_count)
            self.done.emit(self._out_path)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


class FilelistWorker(QThread):
    """Write a metadata listing of *in_paths* to a single output file.

    The *process_fn* has signature ``(Iterable[Path]) -> Iterator[str]`` and
    is responsible for yielding the header and data rows.

    Signals:
        done(Path):  Output path when finished.
        error(str):  Error message; processing stopped.
    """

    done = Signal(Path)
    error = Signal(str)

    def __init__(
        self,
        in_paths: list[Path],
        out_path: Path,
        process_fn: Callable[[Iterable[Path]], Iterator[str]],
        out_encoding: str = "UTF-8",
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._in_paths = in_paths
        self._out_path = out_path
        self._process_fn = process_fn
        self._out_encoding = out_encoding

    def run(self) -> None:
        try:
            with open(
                self._out_path, "w", encoding=self._out_encoding, newline=""
            ) as fh_out:
                for line in self._process_fn(self._in_paths):
                    fh_out.write(line + "\n")
            self.done.emit(self._out_path)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


def _stripped_lines(fh: Iterable[str]) -> Iterator[str]:
    """Yield lines with the trailing newline removed."""
    for line in fh:
        yield line.rstrip("\n")
