"""Main application window."""

from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QAction, QCloseEvent, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from gui.options_dialog import OptionsDialog, load_settings
from gui.worker import CANCELLED, LineCountWorker


class MainWindow(QMainWindow):
    """Main window: menu bar, toolbar, file list table, status bar, drag-and-drop."""

    # Column indices for the file list table.
    COL_NAME = 0
    COL_PATH = 1
    COL_SIZE = 2
    COL_LINES = 3

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PyPanTool")
        self.resize(980, 580)
        self.setAcceptDrops(True)

        # Loaded files: list of Path objects (current input set).
        self._files: list[Path] = []
        # Run counter for %a substitution; increments after each tool run.
        self._run_counter: int = 1
        # Active worker thread (kept alive until done).
        self._worker: QThread | None = None
        # Background line counter for the file list; paused while a tool runs.
        self._count_worker: LineCountWorker | None = None
        self._line_counts: dict[Path, int] = {}
        # Table row of each loaded path.
        self._rows: dict[Path, int] = {}
        # Status text of the running operation (progress is appended to it).
        self._busy_message = ""
        # Set on close so late worker signals do not start new threads.
        self._closing = False

        self._build_ui()
        self._build_menu()
        self._build_toolbar()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(0)

        # Stack: page 0 = drop placeholder, page 1 = file table
        self._stack = QStackedWidget()

        # Page 0 — empty state / drop zone
        placeholder = QLabel(
            "Drop files here\n\nor  File › Open  /  File › Select folder"
        )
        placeholder.setObjectName("dropPlaceholder")
        self._stack.addWidget(placeholder)

        # Page 1 — file list table
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Name", "Path", "Size", "Lines"])
        self._table.horizontalHeader().setSectionResizeMode(
            self.COL_PATH, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            self.COL_NAME, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            self.COL_SIZE, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            self.COL_LINES, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(26)
        self._table.setShowGrid(True)
        self._stack.addWidget(self._table)

        layout.addWidget(self._stack)

        # Status bar
        self._status_label = QLabel("Ready")
        self._progress = QProgressBar()
        self._progress.setMaximumWidth(180)
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._cancel_worker)
        self.statusBar().addWidget(self._status_label, 1)
        self.statusBar().addPermanentWidget(self._progress)
        self.statusBar().addPermanentWidget(self._cancel_btn)

    def _build_menu(self) -> None:
        menubar = self.menuBar()

        # ── File menu ──────────────────────────────────────────────────────────
        file_menu = menubar.addMenu("&File")

        self._act_open = QAction("&Open files…", self)
        self._act_open.setShortcut("Ctrl+O")
        self._act_open.triggered.connect(self._open_files)
        file_menu.addAction(self._act_open)

        self._act_folder = QAction("Select &folder…", self)
        self._act_folder.triggered.connect(self._open_folder)
        file_menu.addAction(self._act_folder)

        file_menu.addSeparator()

        self._act_clear = QAction("&Clear file list", self)
        self._act_clear.triggered.connect(self._clear_files)
        file_menu.addAction(self._act_clear)

        file_menu.addSeparator()

        act_options = QAction("O&ptions…", self)
        act_options.triggered.connect(self._show_options)
        file_menu.addAction(act_options)

        file_menu.addSeparator()

        act_quit = QAction("&Quit", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # ── Tools menu ────────────────────────────────────────────────────────
        self._tools_menu = menubar.addMenu("&Tools")
        self._tools_menu.setEnabled(False)  # enabled once files are loaded

        self._add_tool("E&xtract Columns…", self._run_extract_columns)
        self._add_tool("Extract Matched C&olumns…", self._run_extract_matched_columns)
        self._tools_menu.addSeparator()
        self._add_tool("D&elete Columns…", self._run_delete_columns)
        self._add_tool("Delete Matched Col&umns…", self._run_delete_matched_columns)
        self._add_tool("&Recalculate Columns…", self._run_recalc_columns)
        self._tools_menu.addSeparator()
        self._add_tool("&Extract Lines…", self._run_extract_lines)
        self._add_tool("Extract &Matched Lines…", self._run_extract_matched_lines)
        self._add_tool("Extract 10 min L&ines…", self._run_extract_10min_lines)
        self._tools_menu.addSeparator()
        self._add_tool("&Delete Lines…", self._run_delete_lines)
        self._add_tool("Delete M&atched Lines…", self._run_delete_matched_lines)
        self._tools_menu.addSeparator()
        self._add_tool("Delete &Comment Blocks…", self._run_delete_comments)
        self._add_tool("Delete &Double Lines…", self._run_delete_doubles)
        self._tools_menu.addSeparator()
        self._add_tool("Concatenate by &Lines…", self._run_concat_lines)
        self._add_tool("Concatenate by C&olumns…", self._run_concat_columns)
        self._tools_menu.addSeparator()
        self._add_tool("Split by Line&s…", self._run_split_lines)
        self._add_tool("Split by Colu&mns…", self._run_split_columns)
        self._add_tool("Split Lar&ge File…", self._run_split_large)
        self._tools_menu.addSeparator()
        self._add_tool("Search &One String…", self._run_search_one)
        self._add_tool("&Search and Replace…", self._run_search_replace)
        self._add_tool("Search and Replace &Many…", self._run_search_replace_many)
        self._tools_menu.addSeparator()
        self._add_tool("&Insert Characters at Positions…", self._run_insert_chars)
        self._add_tool("Replace Charac&ters at Positions…", self._run_replace_chars)
        self._tools_menu.addSeparator()
        self._add_tool("Add Colum&n…", self._run_add_column)
        self._add_tool("Add Text L&ine…", self._run_add_line)
        self._add_tool("Add Text &Block…", self._run_add_block)
        self._tools_menu.addSeparator()
        self._add_tool("Save &File List…", self._run_save_filelist)
        self._tools_menu.addSeparator()
        self._add_tool("Re&name Files…", self._run_rename_files)
        self._tools_menu.addSeparator()
        self._add_tool("Compress Files (&zip)", self._run_compress_files_zip)
        self._add_tool("Compress Files (&gz)", self._run_compress_files_gzip)
        self._add_tool("Compress Folder (zip)…", self._run_compress_folder_zip)
        self._add_tool("Compress Folder (tar.gz)…", self._run_compress_folder_targz)
        self._add_tool("Decompress Files", self._run_decompress_files)

        # ── Help menu ──────────────────────────────────────────────────────────
        help_menu = menubar.addMenu("&Help")
        act_about = QAction("&About", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Quick Actions", self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.addToolBar(toolbar)

        toolbar.addAction(self._act_open)
        toolbar.addAction(self._act_folder)
        toolbar.addSeparator()
        toolbar.addAction(self._act_clear)

    # ── File loading ───────────────────────────────────────────────────────────

    def _open_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open files", "", "All files (*)"
        )
        if paths:
            self.add_files([Path(p) for p in paths])

    def _open_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select folder")
        if not folder:
            return
        folder_path = Path(folder)
        files = sorted(
            p for p in folder_path.iterdir()
            if p.is_file() and not p.name.startswith(".")
        )
        if files:
            self.add_files(files)
        else:
            QMessageBox.information(self, "No files", "No files found in that folder.")

    def _clear_files(self) -> None:
        self._stop_line_count()
        self._files.clear()
        self._line_counts.clear()
        self._rows.clear()
        self._table.setRowCount(0)
        self._tools_menu.setEnabled(False)
        self._stack.setCurrentIndex(0)
        self._set_status("Ready")

    # ── Drag and drop ──────────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths: list[Path] = []
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_dir():
                paths.extend(
                    sorted(f for f in p.iterdir() if f.is_file() and not f.name.startswith("."))
                )
            elif p.is_file():
                paths.append(p)
        if paths:
            self.add_files(paths)

    # ── File list management ───────────────────────────────────────────────────

    def add_files(self, paths: list[Path]) -> None:
        """Add *paths* to the file list, skipping already-loaded duplicates."""
        existing = set(self._files)
        new_paths = [p for p in paths if p not in existing]
        for path in new_paths:
            self._files.append(path)
            self._add_table_row(path)
        if new_paths:
            self._stack.setCurrentIndex(1)
            self._tools_menu.setEnabled(True)
            self._set_status(f"{len(self._files)} file(s) loaded")
            self._start_line_count()

    def replace_files(self, paths: list[Path]) -> None:
        """Replace the entire file list (used after a tool run for chaining)."""
        self._stop_line_count()
        self._files = list(paths)
        self._line_counts.clear()
        self._rows.clear()
        self._table.setRowCount(0)
        for path in self._files:
            self._add_table_row(path)
        if self._files:
            self._stack.setCurrentIndex(1)
        else:
            self._stack.setCurrentIndex(0)
        self._tools_menu.setEnabled(bool(self._files))
        self._set_status(f"{len(self._files)} file(s) loaded")
        self._start_line_count()

    def _add_table_row(self, path: Path) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._rows[path] = row
        self._table.setItem(row, self.COL_NAME, QTableWidgetItem(path.name))
        self._table.setItem(row, self.COL_PATH, QTableWidgetItem(str(path.parent)))
        size_kb = path.stat().st_size / 1024 if path.exists() else 0
        self._table.setItem(row, self.COL_SIZE, QTableWidgetItem(f"{size_kb:,.1f} KB"))
        self._table.setItem(row, self.COL_LINES, QTableWidgetItem("—"))

    # ── Line counts (background) ───────────────────────────────────────────────

    def _start_line_count(self) -> None:
        """Count lines of all loaded files not counted yet, in the background."""
        if self._closing or self._worker is not None:
            return  # resumed in _on_worker_finished
        self._stop_line_count()
        todo = [p for p in self._files if p not in self._line_counts]
        if not todo:
            return
        worker = LineCountWorker(todo)
        worker.counted.connect(self._on_line_counted)
        self._count_worker = worker
        worker.start()

    def _stop_line_count(self) -> None:
        """Stop the line counter so no file is held open (e.g. before a rename)."""
        worker = self._count_worker
        if worker is None:
            return
        worker.counted.disconnect(self._on_line_counted)
        worker.requestInterruption()
        worker.wait()
        self._count_worker = None

    def _on_line_counted(self, path: Path, count: int) -> None:
        self._line_counts[path] = count
        row = self._rows.get(path)
        if row is None:
            return
        item = self._table.item(row, self.COL_LINES)
        if item:
            item.setText(f"{count:,}")

    # ── Progress / status helpers ──────────────────────────────────────────────

    def _set_status(self, message: str) -> None:
        self._status_label.setText(message)

    def set_busy(self, message: str) -> None:
        """Switch the UI into busy mode (disables menus, shows progress bar)."""
        self._busy_message = message
        self._set_status(message)
        self._progress.setRange(0, 0)  # indeterminate until progress arrives
        self._progress.setVisible(True)
        self._cancel_btn.setEnabled(True)
        self._cancel_btn.setVisible(True)
        self.menuBar().setEnabled(False)

    def set_idle(self, message: str = "Ready") -> None:
        """Return the UI to idle state."""
        self._busy_message = ""
        self._set_status(message)
        self._progress.setVisible(False)
        self._cancel_btn.setVisible(False)
        self.menuBar().setEnabled(True)

    def _on_line_progress(self, lines: int, percent: int) -> None:
        if not self._busy_message:
            return
        self._progress.setRange(0, 100)
        self._progress.setValue(percent)
        self._set_status(f"{self._busy_message} — {lines:,} lines ({percent} %)")

    # ── Worker wiring helpers (used by tool dialogs) ───────────────────────────

    @property
    def files(self) -> list[Path]:
        """Currently loaded input files."""
        return list(self._files)

    @property
    def run_counter(self) -> int:
        return self._run_counter

    def increment_run_counter(self) -> None:
        self._run_counter += 1

    def current_settings(self) -> dict:
        return load_settings()

    def attach_worker(self, worker: "QThread") -> None:
        """Register and start a worker; connect generic error, progress and
        cancel handling.  Shows the Cancel button even when the caller did not
        call :meth:`set_busy` before."""
        self._stop_line_count()
        self._worker = worker
        worker.finished.connect(self._on_worker_finished)
        worker.error.connect(self._on_worker_error)
        if hasattr(worker, "line_progress"):
            worker.line_progress.connect(self._on_line_progress)
        if not self._busy_message:
            self.set_busy("Working…")
        worker.start()

    def _on_worker_finished(self) -> None:
        self._worker = None
        self._start_line_count()

    def _on_worker_error(self, msg: str) -> None:
        if msg == CANCELLED:
            self.set_idle("Cancelled — partial output removed")
            return
        self.set_idle("Error")
        QMessageBox.warning(self, "Error", msg)

    def _cancel_worker(self) -> None:
        if self._worker is None:
            return
        self._cancel_btn.setEnabled(False)
        self._set_status("Cancelling…")
        self._worker.requestInterruption()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._worker is not None and self._worker.isRunning():
            answer = QMessageBox.question(
                self, "Tool still running",
                "A tool is still running. Cancel it and quit?\n"
                "The output file being written will be removed.",
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._worker.requestInterruption()
            self._worker.wait()
        self._closing = True
        self._stop_line_count()
        event.accept()

    # ── Menu helpers ───────────────────────────────────────────────────────────

    def _add_tool(self, name: str, slot) -> None:
        """Add a named action to the Tools menu connected to *slot*."""
        act = QAction(name, self)
        act.triggered.connect(slot)
        self._tools_menu.addAction(act)

    # ── Tool action handlers ───────────────────────────────────────────────────

    def _run_extract_columns(self) -> None:
        from gui.dialogs.columns_dialog import ColumnsDialog
        ColumnsDialog(self, mode="extract").exec()

    def _run_delete_columns(self) -> None:
        from gui.dialogs.columns_dialog import ColumnsDialog
        ColumnsDialog(self, mode="delete").exec()

    def _run_extract_matched_columns(self) -> None:
        from gui.dialogs.matched_columns_dialog import MatchedColumnsDialog
        MatchedColumnsDialog(self, mode="extract").exec()

    def _run_delete_matched_columns(self) -> None:
        from gui.dialogs.matched_columns_dialog import MatchedColumnsDialog
        MatchedColumnsDialog(self, mode="delete").exec()

    def _run_extract_lines(self) -> None:
        from gui.dialogs.lines_dialog import LinesDialog
        LinesDialog(self, mode="extract").exec()

    def _run_delete_lines(self) -> None:
        from gui.dialogs.lines_dialog import LinesDialog
        LinesDialog(self, mode="delete").exec()

    def _run_extract_matched_lines(self) -> None:
        from gui.dialogs.matched_lines_dialog import MatchedLinesDialog
        MatchedLinesDialog(self, mode="extract").exec()

    def _run_delete_matched_lines(self) -> None:
        from gui.dialogs.matched_lines_dialog import MatchedLinesDialog
        MatchedLinesDialog(self, mode="delete").exec()

    def _run_extract_10min_lines(self) -> None:
        from gui.dialogs.timeseries_dialog import TimeseriesDialog
        TimeseriesDialog(self).exec()

    def _run_insert_chars(self) -> None:
        from gui.dialogs.charpos_dialog import CharPosDialog
        CharPosDialog(self, mode="insert").exec()

    def _run_replace_chars(self) -> None:
        from gui.dialogs.charpos_dialog import CharPosDialog
        CharPosDialog(self, mode="replace").exec()

    def _run_add_column(self) -> None:
        from gui.dialogs.addcol_dialog import AddColumnDialog
        AddColumnDialog(self).exec()

    def _run_add_line(self) -> None:
        from gui.dialogs.addline_dialog import AddLineDialog
        AddLineDialog(self, mode="line").exec()

    def _run_add_block(self) -> None:
        from gui.dialogs.addline_dialog import AddLineDialog
        AddLineDialog(self, mode="block").exec()

    def _run_delete_comments(self) -> None:
        from gui.dialogs.comments_dialog import CommentsDialog
        CommentsDialog(self).exec()

    def _run_delete_doubles(self) -> None:
        from gui.dialogs.doubles_dialog import DoublesDialog
        DoublesDialog(self).exec()

    def _run_concat_lines(self) -> None:
        from gui.dialogs.concat_lines_dialog import ConcatLinesDialog
        ConcatLinesDialog(self).exec()

    def _run_concat_columns(self) -> None:
        from gui.dialogs.concat_columns_dialog import ConcatColumnsDialog
        ConcatColumnsDialog(self).exec()

    def _run_split_lines(self) -> None:
        from gui.dialogs.split_dialog import SplitDialog
        SplitDialog(self, mode="lines").exec()

    def _run_split_columns(self) -> None:
        from gui.dialogs.split_dialog import SplitDialog
        SplitDialog(self, mode="columns").exec()

    def _run_split_large(self) -> None:
        from gui.dialogs.split_dialog import SplitDialog
        SplitDialog(self, mode="large").exec()

    def _run_search_one(self) -> None:
        from gui.dialogs.search_one_dialog import SearchOneDialog
        SearchOneDialog(self).exec()

    def _run_search_replace(self) -> None:
        from gui.dialogs.search_replace_dialog import SearchReplaceDialog
        SearchReplaceDialog(self).exec()

    def _run_search_replace_many(self) -> None:
        from gui.dialogs.search_replace_many_dialog import SearchReplaceManyDialog
        SearchReplaceManyDialog(self).exec()

    def _run_save_filelist(self) -> None:
        from gui.dialogs.filelist_dialog import FilelistDialog
        FilelistDialog(self).exec()

    def _run_recalc_columns(self) -> None:
        from gui.dialogs.recalc_dialog import RecalcDialog
        RecalcDialog(self).exec()

    def _run_rename_files(self) -> None:
        from gui.dialogs.rename_dialog import RenameDialog
        RenameDialog(self).exec()

    def _run_compress_files_zip(self) -> None:
        from core.compress import compress_file_zip
        from gui.run_tool import run_compress
        run_compress(self, compress_file_zip, "Compress (zip)")

    def _run_compress_files_gzip(self) -> None:
        from core.compress import compress_file_gzip
        from gui.run_tool import run_compress
        run_compress(self, compress_file_gzip, "Compress (gz)")

    def _run_compress_folder_zip(self) -> None:
        self._compress_folder(mode="zip")

    def _run_compress_folder_targz(self) -> None:
        self._compress_folder(mode="targz")

    def _compress_folder(self, mode: str) -> None:
        from core.compress import compress_folder_targz, compress_folder_zip
        from gui.run_tool import run_compress

        folder = QFileDialog.getExistingDirectory(self, "Select folder to compress")
        if not folder:
            return
        fn = compress_folder_zip if mode == "zip" else compress_folder_targz
        label = "Compress folder (zip)" if mode == "zip" else "Compress folder (tar.gz)"
        run_compress(self, fn, label, paths=[Path(folder)], replace_list=False)

    def _run_decompress_files(self) -> None:
        from core.compress import decompress_file
        from gui.run_tool import run_compress
        run_compress(self, decompress_file, "Decompress")

    # ── System dialogs ─────────────────────────────────────────────────────────

    def _show_options(self) -> None:
        dlg = OptionsDialog(self)
        dlg.exec()

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About PyPanTool",
            "PyPanTool — Data File Swiss Army Knife\n\n"
            "Batch processing of large tabular text files.\n"
            "Inspired by PANGAEA PanTool.",
        )
