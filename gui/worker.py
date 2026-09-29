"""Background worker threads for file processing.

``ProcessWorker``   — one output per input file (standard tools).
``ConcatWorker``    — all input files merged into one output file.
``FilelistWorker``  — emit file metadata to one output file (no file reading).
``SplitWorker``     — one input file fanned out into numbered output chunks.
``RenameWorker``    — rename files in place.
``CompressWorker``  — apply a file-level operation (compress/decompress) per path.
``LineCountWorker`` — count lines of loaded files for the file list.

The three streaming workers share :class:`_StreamWorker`: it meters the input
stream, reports progress and honours cancellation (``requestInterruption``)
every ``PROGRESS_INTERVAL`` input lines.  A cancelled or failed run removes
the partial output it was writing and emits ``error(CANCELLED)`` or
``error(message)``.
"""

import contextlib
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Any

from PySide6.QtCore import QFile, QThread, Signal

from core.filelist import count_newlines
from core.naming import input_matcher, output_problem

CANCELLED = "Cancelled by user."


class _Cancelled(Exception):
    pass


class _StreamWorker(QThread):
    """Base for workers that stream text lines from input files.

    Signals:
        line_progress(int, int): (input lines read so far, percent 0-100).
        error(str):              Error message or :data:`CANCELLED`.
    """

    line_progress = Signal(int, int)
    error = Signal(str)

    # Emit progress / check for cancel every this many input lines.
    PROGRESS_INTERVAL = 5_000

    def _reset_meter(self, total_bytes: int) -> None:
        self._total_bytes = max(total_bytes, 1)
        self._read_bytes = 0
        self._read_lines = 0

    def _metered(self, lines: Iterable[str]) -> Iterator[str]:
        """Pass *lines* through while counting them for progress and cancel."""
        for line in lines:
            # Characters approximate bytes; exact enough for a progress bar.
            self._read_bytes += len(line) + 1
            self._read_lines += 1
            if self._read_lines % self.PROGRESS_INTERVAL == 0:
                if self.isInterruptionRequested():
                    raise _Cancelled
                self._emit_progress()
            yield line

    def _emit_progress(self) -> None:
        percent = min(100, self._read_bytes * 100 // self._total_bytes)
        self.line_progress.emit(self._read_lines, percent)

    def _open_lines(self, path: Path, encoding: str) -> Iterator[str]:
        """Open *path* on first read; yield metered lines without newline."""
        with open(path, encoding=encoding, errors="replace") as fh:
            yield from self._metered(_stripped_lines(fh))


class ProcessWorker(_StreamWorker):
    """Run a streaming core function over one or more files in a background thread.

    Signals:
        file_started(int, int, str):
            Emitted when a new file begins processing.
            Args: (1-based file index, total files, file name)
        file_done(int, Path):
            Emitted when a file finishes.
            Args: (1-based file index, output path)
        all_done():
            Emitted when all files have been processed.
    """

    file_started = Signal(int, int, str)
    file_done = Signal(int, Path)
    all_done = Signal()

    def __init__(
        self,
        jobs: list[tuple[Path, Path]],
        process_fn: Callable[[Iterable[str]], Iterator[str]],
        in_encoding: str = "UTF-8",
        out_encoding: str = "UTF-8",
        pass_path: bool = False,
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
            pass_path:   When ``True``, the current input path is passed as a
                         second positional argument to *process_fn* (used by
                         tools that embed file metadata, e.g. Add Column).
        """
        super().__init__(parent)
        self._jobs = jobs
        self._process_fn = process_fn
        self._in_encoding = in_encoding
        self._out_encoding = out_encoding
        self._pass_path = pass_path

    # ── QThread entry point ───────────────────────────────────────────────────

    def run(self) -> None:
        problem = output_problem([i for i, _ in self._jobs], [o for _, o in self._jobs])
        if problem:
            self.error.emit(problem)
            return
        total = len(self._jobs)
        for idx, (in_path, out_path) in enumerate(self._jobs, start=1):
            self.file_started.emit(idx, total, in_path.name)
            try:
                self._process_one(in_path, out_path)
            except _Cancelled:
                self.error.emit(CANCELLED)
                return
            except Exception as exc:  # noqa: BLE001
                self.error.emit(f"{in_path.name}: {exc}")
                return
            self.file_done.emit(idx, out_path)
        self.all_done.emit()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _process_one(self, in_path: Path, out_path: Path) -> None:
        self._reset_meter(in_path.stat().st_size)
        lines = self._open_lines(in_path, self._in_encoding)
        with _output(out_path, self._out_encoding) as fh_out:
            if self._pass_path:
                out_lines = self._process_fn(lines, in_path)
            else:
                out_lines = self._process_fn(lines)
            for out_line in out_lines:
                fh_out.write(out_line + "\n")
        # Final progress tick so the GUI always reaches the real line count.
        self._emit_progress()


class ConcatWorker(_StreamWorker):
    """Merge N input files into one output file in a background thread.

    The *process_fn* receives an iterable of ``(filename, line_stream)`` pairs
    and returns an ``Iterator[str]``.  Each input file is opened only when the
    function first reads from it and closed when its stream is exhausted, so
    sequential concatenation holds one file open at a time; concat-by-columns
    still reads all of them in parallel.

    When *trash_inputs* is True, the input files are moved to the recycle bin
    after the output has been written completely.  Inputs that could not be
    trashed are listed in :attr:`trash_failures` when ``done`` is emitted.
    On error or cancel, the partial output file is removed and no input is
    touched.

    Signals:
        done(Path): Output path when finished successfully.
    """

    done = Signal(Path)

    def __init__(
        self,
        in_paths: list[Path],
        out_path: Path,
        process_fn: Callable[[Iterable[tuple[str, Iterable[str]]]], Iterator[str]],
        in_encoding: str = "UTF-8",
        out_encoding: str = "UTF-8",
        trash_inputs: bool = False,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._in_paths = in_paths
        self._out_path = out_path
        self._process_fn = process_fn
        self._in_encoding = in_encoding
        self._out_encoding = out_encoding
        self._trash_inputs = trash_inputs
        self.trash_failures: list[str] = []

    def run(self) -> None:
        problem = output_problem(self._in_paths, [self._out_path])
        if problem:
            self.error.emit(problem)
            return
        try:
            self._write()
        except _Cancelled:
            self.error.emit(CANCELLED)
            return
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))
            return
        if self._trash_inputs:
            self.trash_failures = [
                p.name for p in self._in_paths if not _move_to_trash(p)
            ]
        self.done.emit(self._out_path)

    def _write(self) -> None:
        self._reset_meter(sum(p.stat().st_size for p in self._in_paths))
        inputs = (
            (p.name, self._open_lines(p, self._in_encoding)) for p in self._in_paths
        )
        with _output(self._out_path, self._out_encoding) as fh_out:
            for out_line in self._process_fn(inputs):
                fh_out.write(out_line + "\n")
        self._emit_progress()


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
        problem = output_problem(self._in_paths, [self._out_path])
        if problem:
            self.error.emit(problem)
            return
        try:
            with open(
                self._out_path, "w", encoding=self._out_encoding, newline=""
            ) as fh_out:
                for line in self._process_fn(self._in_paths):
                    fh_out.write(line + "\n")
            self.done.emit(self._out_path)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


class SplitWorker(_StreamWorker):
    """Fan each input file out into numbered chunk files.

    The *process_fn* has signature ``(Iterable[str]) -> Iterator[tuple[int, str]]``
    and yields ``(1-based chunk index, line)`` pairs.  Chunk *k* of input
    ``data.tab`` is written to ``data_000k.tab`` next to the input.

    When *sequential* is ``True`` (line-based splits), chunk indices are
    monotonic and each chunk file is closed as soon as the next one starts, so
    only one output is open at a time.  When ``False`` (column splits), all
    chunk files stay open until the input is exhausted.

    On error or cancel, the chunks of the file being split are removed;
    chunks of earlier files are kept.

    Signals:
        file_started(int, int, str): (1-based input index, total inputs, name).
        all_done(list):              Every chunk Path created, in creation order.
    """

    file_started = Signal(int, int, str)
    all_done = Signal(list)

    def __init__(
        self,
        in_paths: list[Path],
        process_fn: Callable[[Iterable[str]], Iterator[tuple[int, str]]],
        sequential: bool = True,
        in_encoding: str = "UTF-8",
        out_encoding: str = "UTF-8",
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._in_paths = in_paths
        self._process_fn = process_fn
        self._sequential = sequential
        self._in_encoding = in_encoding
        self._out_encoding = out_encoding

    def run(self) -> None:
        total = len(self._in_paths)
        created: list[Path] = []
        is_input = input_matcher(self._in_paths)
        for idx, in_path in enumerate(self._in_paths, start=1):
            self.file_started.emit(idx, total, in_path.name)
            current: list[Path] = []
            try:
                self._split_one(in_path, current, is_input)
            except _Cancelled:
                for p in current:
                    _remove(p)
                self.error.emit(CANCELLED)
                return
            except Exception as exc:  # noqa: BLE001
                for p in current:
                    _remove(p)
                self.error.emit(f"{in_path.name}: {exc}")
                return
            created.extend(current)
        self.all_done.emit(created)

    def _split_one(
        self, in_path: Path, created: list[Path], is_input: Callable[[Path], bool]
    ) -> None:
        self._reset_meter(in_path.stat().st_size)
        lines = self._open_lines(in_path, self._in_encoding)
        with contextlib.ExitStack() as stack:
            handles: dict[int, Any] = {}
            for chunk_idx, line in self._process_fn(lines):
                fh = handles.get(chunk_idx)
                if fh is None:
                    if self._sequential:
                        for open_fh in handles.values():
                            open_fh.close()
                        handles.clear()
                    out_path = in_path.with_name(
                        f"{in_path.stem}_{chunk_idx:04d}{in_path.suffix}"
                    )
                    if is_input(out_path):
                        raise ValueError(f"Chunk {out_path.name} would overwrite a loaded file.")
                    fh = stack.enter_context(
                        open(out_path, "w", encoding=self._out_encoding, newline="")
                    )
                    handles[chunk_idx] = fh
                    created.append(out_path)
                fh.write(line + "\n")
        self._emit_progress()


class RenameWorker(QThread):
    """Rename files in place on a background thread.

    If a rename fails, ``all_done`` is still emitted with the paths as they
    are on disk (renamed ones new, the rest old) so the file list stays
    valid, followed by ``error``.

    Signals:
        file_renamed(int, int, str, Path):
            Emitted for each renamed file: (1-based index, total, old_name, new_path).
        all_done(list):
            Current Path list after the renames.
        error(str):
            Emitted on first failure; processing stops.
    """

    file_renamed = Signal(int, int, str, Path)
    all_done = Signal(list)
    error = Signal(str)

    def __init__(self, pairs: list[tuple[Path, Path]], parent: Any = None) -> None:
        super().__init__(parent)
        self._pairs = pairs

    def run(self) -> None:
        total = len(self._pairs)
        new_paths: list[Path] = []
        for idx, (old_path, new_path) in enumerate(self._pairs, start=1):
            if old_path == new_path:
                new_paths.append(new_path)
                continue
            try:
                old_path.rename(new_path)
            except OSError as exc:
                remaining = [old for old, _ in self._pairs[idx - 1:]]
                self.all_done.emit(new_paths + remaining)
                self.error.emit(f"{old_path.name}: {exc}")
                return
            self.file_renamed.emit(idx, total, old_path.name, new_path)
            new_paths.append(new_path)
        self.all_done.emit(new_paths)


class CompressWorker(QThread):
    """Apply a file-level operation to each path in a background thread.

    The *file_fn* receives one :class:`~pathlib.Path` and returns the produced
    path or a list of produced paths (compression returns the archive,
    decompression may return several extracted files).  Cancellation is
    checked between files.

    Signals:
        file_started(int, int, str): (1-based index, total, file name).
        all_done(list):              Every produced Path, in order.
        error(str):                  Error message or :data:`CANCELLED`.
    """

    file_started = Signal(int, int, str)
    all_done = Signal(list)
    error = Signal(str)

    def __init__(
        self,
        paths: list[Path],
        file_fn: Callable[[Path], Path | list[Path]],
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._paths = paths
        self._file_fn = file_fn

    def run(self) -> None:
        total = len(self._paths)
        produced: list[Path] = []
        for idx, path in enumerate(self._paths, start=1):
            if self.isInterruptionRequested():
                self.error.emit(CANCELLED)
                return
            self.file_started.emit(idx, total, path.name)
            try:
                result = self._file_fn(path)
            except Exception as exc:  # noqa: BLE001
                self.error.emit(f"{path.name}: {exc}")
                return
            produced.extend(result if isinstance(result, list) else [result])
        self.all_done.emit(produced)


class LineCountWorker(QThread):
    """Count the lines of each path in the background (for the file list).

    Reads in 1 MiB binary chunks; stops quietly on ``requestInterruption``.
    Unreadable files are skipped.

    Signals:
        counted(object, int): (Path, line count).
    """

    counted = Signal(object, int)

    _CHUNK = 1024 * 1024

    def __init__(self, paths: list[Path], parent: Any = None) -> None:
        super().__init__(parent)
        self._paths = paths

    def run(self) -> None:
        for path in self._paths:
            if self.isInterruptionRequested():
                return
            try:
                count = count_newlines(self._chunks(path))
            except (OSError, _Cancelled):
                continue
            self.counted.emit(path, count)

    def _chunks(self, path: Path) -> Iterator[bytes]:
        with open(path, "rb") as fh:
            while chunk := fh.read(self._CHUNK):
                if self.isInterruptionRequested():
                    raise _Cancelled
                yield chunk


# ── Helpers ───────────────────────────────────────────────────────────────────

def _stripped_lines(fh: Iterable[str]) -> Iterator[str]:
    """Yield lines with the trailing newline removed."""
    for line in fh:
        yield line.rstrip("\n")


@contextlib.contextmanager
def _output(path: Path, encoding: str) -> Iterator[Any]:
    """Open *path* for writing; delete it again if the block fails."""
    with open(path, "w", encoding=encoding, newline="") as fh:
        try:
            yield fh
        except BaseException:
            fh.close()
            _remove(path)
            raise


def _remove(path: Path) -> None:
    with contextlib.suppress(OSError):
        path.unlink()


def _move_to_trash(path: Path) -> bool:
    """Move *path* to the system recycle bin; True on success."""
    result = QFile.moveToTrash(str(path))
    ok = result[0] if isinstance(result, tuple) else bool(result)
    return ok and not path.exists()
