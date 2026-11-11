"""Main application window.

Layout, top to bottom: menu bar, toolbar (file actions and the current
settings), context line, then a vertical splitter with the file list, the
peek pane (first lines of the selected file) and the journal (one line per
tool run).  The status bar shows progress.
"""

import os
import time
from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QAction, QCloseEvent, QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.header import header_finder, is_comment
from core.recalc import PLAIN_NUMBER
from gui.options_dialog import OptionsDialog, load_settings, table_options
from gui.peek import PEEK_LINES, head_lines
from gui.style import AMBER, MUTED, TEAL, mono_font
from gui.worker import CANCELLED, LineCountWorker

_DELIMITER_NAMES = {"\t": "tab", ";": "semicolon", ",": "comma", "|": "pipe", " ": "space"}
_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
_MAX_PEEK_COLUMNS = 200


def human_size(size: int) -> str:
    """File size in SI units (1 kB = 1000 B)."""
    if size < 1000:
        return f"{size} B"
    for unit, factor in (("kB", 1e3), ("MB", 1e6), ("GB", 1e9)):
        if size < factor * 1000 or unit == "GB":
            return f"{size / factor:,.1f} {unit}"
    return f"{size} B"


class MainWindow(QMainWindow):
    """Main window: menus, toolbar, file list, peek pane, journal, status bar."""

    # Column indices for the file list table.
    COL_NAME = 0
    COL_FOLDER = 1
    COL_SIZE = 2
    COL_LINES = 3
    COL_COLS = 4
    COL_SNIFF = 5

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PyPanTool")
        self.resize(1080, 700)
        self.setAcceptDrops(True)

        # Loaded files: list of Path objects (current input set).
        self._files: list[Path] = []
        # Earlier file sets, newest last (for "Step back").
        self._history: list[list[Path]] = []
        # Run counter for %a substitution; increments after each tool run.
        self._run_counter: int = 1
        # Active worker thread (kept alive until done).
        self._worker: QThread | None = None
        # Background sniff + line counter for the file list; paused while a tool runs.
        self._count_worker: LineCountWorker | None = None
        self._line_counts: dict[Path, int] = {}
        self._sniffed: set[Path] = set()
        # Table row of each loaded path.
        self._rows: dict[Path, int] = {}
        # Status text of the running operation (progress is appended to it).
        self._busy_message = ""
        # Journal: finished runs, and the run in progress.
        self._journal: list[dict] = []
        self._pending: dict | None = None
        # Set on close so late worker signals do not start new threads.
        self._closing = False

        self._build_ui()
        self._build_menu()
        self._build_toolbar()
        self._refresh_context()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Context line: what is loaded, and from where.
        context_row = QHBoxLayout()
        context_row.setContentsMargins(14, 9, 14, 9)
        context_row.setSpacing(10)
        self._context = QLabel()
        self._context.setObjectName("context")
        self._context_folder = QLabel()
        self._context_folder.setObjectName("monoMuted")
        self._context_folder.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        context_row.addWidget(self._context)
        context_row.addWidget(self._context_folder, 1)
        layout.addLayout(context_row)

        # Stack: page 0 = drop placeholder, page 1 = file list / peek / journal
        self._stack = QStackedWidget()
        placeholder = QLabel(
            "Drop files or folders here\n\nor  File › Open files  /  File › Select folder"
        )
        placeholder.setObjectName("dropPlaceholder")
        self._stack.addWidget(placeholder)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_file_table())
        splitter.addWidget(self._build_peek())
        splitter.addWidget(self._build_journal())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([250, 250, 110])
        self._stack.addWidget(splitter)
        layout.addWidget(self._stack, 1)

        # Status bar
        self._status_label = QLabel("Ready")
        self._progress = QProgressBar()
        self._progress.setMaximumWidth(180)
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._cancel_worker)
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().addWidget(self._status_label, 1)
        self.statusBar().addPermanentWidget(self._progress)
        self.statusBar().addPermanentWidget(self._cancel_btn)
        self.statusBar().addPermanentWidget(QLabel("Ctrl+K  find tool"))

    def _build_file_table(self) -> QTableWidget:
        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(
            ["NAME", "FOLDER", "SIZE", "LINES", "COLS", "FIRST 64 kB"]
        )
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setHighlightSections(False)
        for col, width in ((self.COL_FOLDER, 200), (self.COL_SIZE, 90),
                           (self.COL_LINES, 100), (self.COL_COLS, 60),
                           (self.COL_SNIFF, 280)):
            table.setColumnWidth(col, width)
        left = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        for col in range(6):
            numeric = col in (self.COL_SIZE, self.COL_LINES, self.COL_COLS)
            table.horizontalHeaderItem(col).setTextAlignment(_RIGHT if numeric else left)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(24)
        table.cellDoubleClicked.connect(lambda _row, _col: self._run_stats())
        table.currentCellChanged.connect(lambda *_: self._refresh_peek())
        self._table = table
        return table

    def _build_peek(self) -> QWidget:
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        head = QHBoxLayout()
        head.setContentsMargins(14, 7, 14, 6)
        head.setSpacing(10)
        caption = QLabel("PEEK")
        caption.setObjectName("caption")
        self._peek_name = QLabel()
        self._peek_info = QLabel()
        self._peek_info.setObjectName("monoMuted")
        head.addWidget(caption)
        head.addWidget(self._peek_name)
        head.addStretch(1)
        head.addWidget(self._peek_info)
        layout.addLayout(head)

        table = QTableWidget(0, 0)
        table.setObjectName("peek")
        table.setFont(mono_font())
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.ContiguousSelection)
        table.verticalHeader().setDefaultSectionSize(21)
        table.verticalHeader().setDefaultAlignment(_RIGHT)
        table.horizontalHeader().setHighlightSections(False)
        table.verticalHeader().setHighlightSections(False)
        self._peek = table
        layout.addWidget(table, 1)
        return pane

    def _build_journal(self) -> QWidget:
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        head = QHBoxLayout()
        head.setContentsMargins(14, 7, 8, 6)
        caption = QLabel("JOURNAL")
        caption.setObjectName("caption")
        self._back_btn = QPushButton("Step back  Ctrl+Z")
        self._save_journal_btn = QPushButton("Save journal…")
        for button in (self._back_btn, self._save_journal_btn):
            button.setObjectName("link")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setEnabled(False)
        self._back_btn.clicked.connect(self._step_back)
        self._save_journal_btn.clicked.connect(self._save_journal)
        head.addWidget(caption)
        head.addStretch(1)
        head.addWidget(self._back_btn)
        head.addWidget(self._save_journal_btn)
        layout.addLayout(head)

        table = QTableWidget(0, 6)
        table.setFont(mono_font())
        table.horizontalHeader().setVisible(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(21)
        table.setShowGrid(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for col, width in ((0, 84), (1, 210), (3, 90), (4, 220), (5, 80)):
            table.setColumnWidth(col, width)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._journal_table = table
        layout.addWidget(table, 1)
        return pane

    def _build_menu(self) -> None:
        menubar = self.menuBar()
        self._tool_menus: list = []
        self._tool_actions: list[tuple[str, QAction]] = []

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

        self._act_stats = QAction("File S&tatistics…", self)
        self._act_stats.setShortcut("Ctrl+I")
        self._act_stats.setToolTip(
            "Scan the selected file: min/max per column, missing-value markers,\n"
            "encoding, line endings, row width (Ctrl+I or double-click a file)"
        )
        self._act_stats.triggered.connect(self._run_stats)
        file_menu.addAction(self._act_stats)

        self._act_back = QAction("Step &back to previous files", self)
        self._act_back.setShortcut("Ctrl+Z")
        self._act_back.triggered.connect(self._step_back)
        file_menu.addAction(self._act_back)

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

        # ── Tool menus, grouped by what they work on ──────────────────────────
        self._add_tool_menu("&Columns", [
            ("&Extract Columns…", self._run_extract_columns),
            ("Extract &Matched Columns…", self._run_extract_matched_columns),
            None,
            ("&Delete Columns…", self._run_delete_columns),
            ("Delete M&atched Columns…", self._run_delete_matched_columns),
            None,
            ("&Recalculate Columns…", self._run_recalc_columns),
            ("Convert Date/Time to &ISO 8601…", self._run_convert_datetime),
            ("Add Colum&n…", self._run_add_column),
        ])
        self._add_tool_menu("&Lines", [
            ("&Extract Lines…", self._run_extract_lines),
            ("Extract &Matched Lines…", self._run_extract_matched_lines),
            ("Extract &10 min Lines…", self._run_extract_10min_lines),
            None,
            ("&Delete Lines…", self._run_delete_lines),
            ("Delete M&atched Lines…", self._run_delete_matched_lines),
            ("Delete &Comment Blocks…", self._run_delete_comments),
            ("Delete Do&uble Lines…", self._run_delete_doubles),
            None,
            ("Add Text &Line…", self._run_add_line),
            ("Add Text &Block…", self._run_add_block),
        ])
        self._add_tool_menu("&Text", [
            ("Search &One String…", self._run_search_one),
            ("&Search and Replace…", self._run_search_replace),
            ("Search and Replace &Many…", self._run_search_replace_many),
            None,
            ("&Insert Characters at Positions…", self._run_insert_chars),
            ("&Replace Characters at Positions…", self._run_replace_chars),
        ])
        self._add_tool_menu("Combine / &Split", [
            ("Concatenate by &Lines…", self._run_concat_lines),
            ("Concatenate by &Columns…", self._run_concat_columns),
            None,
            ("Split by L&ines…", self._run_split_lines),
            ("Split by C&olumns…", self._run_split_columns),
            ("Split Lar&ge File…", self._run_split_large),
        ])
        self._add_tool_menu("F&iles", [
            ("Save &File List…", self._run_save_filelist),
            ("&Rename Files…", self._run_rename_files),
            None,
            ("Compress Files (&zip)", self._run_compress_files_zip),
            ("Compress Files (&gz)", self._run_compress_files_gzip),
            ("&Decompress Files", self._run_decompress_files),
        ])
        # Folder compression picks its own folder, so it works without loaded files.
        files_menu = self._tool_menus[-1]
        files_menu.addSeparator()
        for name, slot in (("Compress F&older (zip)…", self._run_compress_folder_zip),
                           ("Compress Folder (&tar.gz)…", self._run_compress_folder_targz)):
            act = QAction(name, self)
            act.triggered.connect(slot)
            files_menu.addAction(act)

        # ── Help menu ──────────────────────────────────────────────────────────
        help_menu = menubar.addMenu("&Help")
        act_find = QAction("&Find Tool…", self)
        act_find.setShortcut("Ctrl+K")
        act_find.triggered.connect(self._find_tool)
        help_menu.addAction(act_find)
        act_about = QAction("&About", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _add_tool_menu(self, title: str, entries: list) -> None:
        """Add a menu of tools that need loaded files (``None`` = separator)."""
        menu = self.menuBar().addMenu(title)
        self._tool_menus.append(menu)
        group = title.replace("&", "")
        for entry in entries:
            if entry is None:
                menu.addSeparator()
                continue
            name, slot = entry
            act = QAction(name, self)
            act.triggered.connect(slot)
            menu.addAction(act)
            self._tool_actions.append((group, act))

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Quick Actions", self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.addToolBar(toolbar)
        self._toolbar = toolbar

        toolbar.addAction(self._act_open)
        toolbar.addAction(self._act_folder)
        toolbar.addAction(self._act_clear)
        toolbar.addSeparator()
        toolbar.addAction(self._act_stats)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # Current settings, always visible; click to change them.
        self._settings_chip = QToolButton()
        self._settings_chip.setObjectName("settingsChip")
        self._settings_chip.setToolTip("Settings used by every tool. Click to change.")
        self._settings_chip.clicked.connect(self._show_options)
        toolbar.addWidget(self._settings_chip)

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
        if self._files:
            self._history.append(list(self._files))
        self._set_files([])
        self._set_status("Ready")

    # ── Drag and drop ──────────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() and self._worker is None:
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
        new_paths = [p for p in dict.fromkeys(paths) if p not in existing]
        if not new_paths:
            return
        for path in new_paths:
            self._files.append(path)
            self._add_table_row(path)
        self._after_list_change()
        self._set_status(f"{len(self._files)} file(s) loaded")

    def replace_files(self, paths: list[Path]) -> None:
        """Replace the entire file list (used after a tool run for chaining).

        The previous list is remembered for "Step back".
        """
        if self._files and list(paths) != self._files:
            self._history.append(list(self._files))
        if self._pending is not None:
            self._pending["outputs"] = list(paths)
        self._set_files(list(paths))
        self._set_status(f"{len(self._files)} file(s) loaded")

    def _set_files(self, paths: list[Path]) -> None:
        self._stop_line_count()
        self._files = paths
        self._line_counts.clear()
        self._sniffed.clear()
        self._rows.clear()
        self._table.setRowCount(0)
        for path in self._files:
            self._add_table_row(path)
        self._after_list_change()

    def _after_list_change(self) -> None:
        has_files = bool(self._files)
        self._stack.setCurrentIndex(1 if has_files else 0)
        folders = {p.parent for p in self._files}
        self._table.setColumnHidden(self.COL_FOLDER, len(folders) <= 1)
        if has_files and self._table.currentRow() < 0:
            self._table.selectRow(0)
        self._refresh_context()
        self._refresh_actions()
        self._refresh_peek()
        self._start_line_count()

    def _add_table_row(self, path: Path) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._rows[path] = row
        name = QTableWidgetItem(path.name)
        name.setToolTip(str(path))
        self._table.setItem(row, self.COL_NAME, name)
        folder = QTableWidgetItem(str(path.parent))
        folder.setForeground(QColor(MUTED))
        self._table.setItem(row, self.COL_FOLDER, folder)
        try:
            size_text = human_size(path.stat().st_size)
        except OSError:
            size_text = "missing"
        for col, text in ((self.COL_SIZE, size_text), (self.COL_LINES, "…"),
                          (self.COL_COLS, ""), (self.COL_SNIFF, "")):
            item = QTableWidgetItem(text)
            item.setFont(mono_font())
            if col != self.COL_SNIFF:
                item.setTextAlignment(_RIGHT)
            self._table.setItem(row, col, item)

    def _refresh_context(self) -> None:
        if not self._files:
            self._context.setText("No files loaded")
            self._context_folder.setText("")
            return
        total = 0
        for path in self._files:
            try:
                total += path.stat().st_size
            except OSError:
                pass
        count = len(self._files)
        self._context.setText(
            f"{count} file{'s' if count != 1 else ''}  ·  {human_size(total)}"
        )
        try:
            folder = os.path.commonpath([str(p.parent) for p in self._files])
        except ValueError:
            folder = "several drives"
        self._context_folder.setText(folder)

    def _refresh_actions(self) -> None:
        idle = self._worker is None
        has_files = bool(self._files)
        for menu in self._tool_menus:
            for act in menu.actions():
                if any(act is tool for _, tool in self._tool_actions):
                    act.setEnabled(has_files)
        self._act_stats.setEnabled(has_files)
        self._act_clear.setEnabled(has_files)
        self._act_back.setEnabled(bool(self._history) and idle)
        self._back_btn.setEnabled(bool(self._history) and idle)
        self._save_journal_btn.setEnabled(bool(self._journal))
        settings = load_settings()
        delimiter = _DELIMITER_NAMES.get(settings["delimiter"], repr(settings["delimiter"]))
        self._settings_chip.setText(
            f"{delimiter}  ·  {settings['in_encoding']} → {settings['out_encoding']}"
            f"  ·  header ≥ line {settings['header_line']}  ·  {settings['pattern']}"
        )

    # ── Sniff and line counts (background) ─────────────────────────────────────

    def _start_line_count(self) -> None:
        """Sniff and count all loaded files not done yet, in the background."""
        if self._closing or self._worker is not None:
            return  # resumed in _on_worker_finished
        self._stop_line_count()
        to_count = [p for p in self._files if p not in self._line_counts]
        to_sniff = [p for p in self._files if p not in self._sniffed]
        if not to_count and not to_sniff:
            return
        settings = load_settings()
        worker = LineCountWorker(
            to_count, to_sniff, settings["in_encoding"], table_options(settings)
        )
        worker.counted.connect(self._on_line_counted)
        worker.sniffed.connect(self._on_sniffed)
        self._count_worker = worker
        worker.start()

    def _stop_line_count(self) -> None:
        """Stop the background reader so no file is held open (e.g. before a rename)."""
        worker = self._count_worker
        if worker is None:
            return
        worker.counted.disconnect(self._on_line_counted)
        worker.sniffed.disconnect(self._on_sniffed)
        worker.requestInterruption()
        worker.wait()
        self._count_worker = None

    def _on_line_counted(self, path: Path, count: int) -> None:
        self._line_counts[path] = count
        row = self._rows.get(path)
        if row is not None:
            self._table.item(row, self.COL_LINES).setText(f"{count:,}")
        self._fill_journal_lines()

    def _on_sniffed(self, path: Path, profile) -> None:
        self._sniffed.add(path)
        row = self._rows.get(path)
        if row is None:
            return
        encoding = load_settings()["in_encoding"]
        notes: list[str] = []
        attention = False
        if profile.invalid_lines:
            notes.append(f"not {encoding} (byte 0x{profile.invalid_first_byte:02X}, "
                         f"line {profile.invalid_first_line:,})")
            attention = True
        else:
            notes.append(encoding + (" with BOM" if profile.has_bom else ""))
        endings = [name for count, name in ((profile.crlf, "CRLF"), (profile.lf, "LF"),
                                             (profile.cr, "CR")) if count]
        if len(endings) > 1:
            notes.append("mixed line endings")
            attention = True
        elif endings:
            notes.append(endings[0])
        cols_item = self._table.item(row, self.COL_COLS)
        if not profile.header_lineno:
            notes.append("no header found")
            cols_item.setText("–")
            attention = True
        elif profile.ragged_rows:
            low = min(profile.ragged_min, len(profile.columns))
            high = max(profile.ragged_max, len(profile.columns))
            cols_item.setText(f"{low}–{high}")
            cols_item.setForeground(QColor(AMBER))
            notes.append("ragged rows")
            attention = True
        else:
            cols_item.setText(str(len(profile.columns)))
        item = self._table.item(row, self.COL_SNIFF)
        item.setText("  ·  ".join(notes))
        item.setForeground(QColor(AMBER if attention else MUTED))
        if attention:
            item.setToolTip("Run File Statistics (Ctrl+I) for details.")

    # ── Peek pane ──────────────────────────────────────────────────────────────

    def _selected_path(self) -> Path | None:
        row = self._table.currentRow()
        if row < 0 and len(self._files) == 1:
            row = 0
        return self._files[row] if 0 <= row < len(self._files) else None

    def _refresh_peek(self) -> None:
        """Show the first lines of the selected file with column numbers."""
        table = self._peek
        table.clear()
        table.clearSpans()
        table.setRowCount(0)
        table.setColumnCount(0)
        path = self._selected_path()
        self._peek_name.setText(path.name if path else "")
        self._peek_info.setText("")
        if path is None:
            return
        settings = load_settings()
        options = table_options(settings)
        try:
            lines = head_lines(path, settings["in_encoding"])
        except (OSError, LookupError) as exc:
            self._peek_info.setText(str(exc))
            return

        delimiter, prefix = options["delimiter"], options["comment_prefix"]
        is_header = header_finder(options["header_line"], prefix, delimiter)
        header_no = 0
        rows: list[list[str] | None] = []   # None = show the line unsplit
        for lineno, line in enumerate(lines, start=1):
            if not header_no:
                if is_header(lineno, line):
                    header_no = lineno
                    rows.append(line.split(delimiter))
                else:
                    rows.append(None)
            elif delimiter not in line or is_comment(line, prefix):
                rows.append(None)
            else:
                rows.append(line.split(delimiter))
        width = min(max((len(r) for r in rows if r), default=1), _MAX_PEEK_COLUMNS)

        table.setColumnCount(width)
        table.setRowCount(len(rows))
        table.setHorizontalHeaderLabels([str(i) for i in range(1, width + 1)])
        table.setVerticalHeaderLabels([str(i) for i in range(1, len(rows) + 1)])
        for r, (cells, line) in enumerate(zip(rows, lines)):
            if cells is None:
                item = QTableWidgetItem(line)
                item.setForeground(QColor(MUTED))
                table.setItem(r, 0, item)
                if width > 1:
                    table.setSpan(r, 0, 1, width)
                continue
            for c, text in enumerate(cells[:width]):
                item = QTableWidgetItem(text)
                if r + 1 == header_no:
                    item.setFont(mono_font(bold=True))
                    item.setForeground(QColor(TEAL))
                elif PLAIN_NUMBER.fullmatch(text.strip()):
                    item.setTextAlignment(_RIGHT)
                table.setItem(r, c, item)
        table.resizeColumnsToContents()
        for c in range(width):
            table.setColumnWidth(c, min(max(table.columnWidth(c) + 10, 70), 320))
        more = "first " if len(lines) >= PEEK_LINES else ""
        header_text = f"header = line {header_no}" if header_no else "no header found"
        self._peek_info.setText(f"{more}{len(lines)} lines  ·  {header_text}")

    # ── Journal and step back ──────────────────────────────────────────────────

    def _total_lines(self, paths: list[Path]) -> int | None:
        if not paths or any(p not in self._line_counts for p in paths):
            return None
        return sum(self._line_counts[p] for p in paths)

    def _finish_journal_entry(self, status: str) -> None:
        entry = self._pending
        self._pending = None
        if entry is None:
            return
        entry["status"] = entry.get("status") or status
        entry["seconds"] = time.monotonic() - entry.pop("t0")
        self._journal.append(entry)
        row = self._journal_table.rowCount()
        self._journal_table.insertRow(row)
        outputs = entry.get("outputs")
        files = str(len(entry["inputs"]))
        if outputs is not None:
            files += f" → {len(outputs)}"
        shown = entry["label"] if entry["status"] == "done" else (
            f"{entry['label']} ({entry['status']})")
        cells = (entry["time"].astimezone().strftime("%H:%M:%S"), shown,
                 entry["detail"], f"{files} files", "", f"{entry['seconds']:.1f} s")
        for col, text in enumerate(cells):
            item = QTableWidgetItem(text)
            if col in (0, 5):
                item.setForeground(QColor(MUTED))
            if entry["status"] != "done" and col == 1:
                item.setForeground(QColor(AMBER))
            if col >= 3:
                item.setTextAlignment(_RIGHT)
            item.setToolTip(text)
            self._journal_table.setItem(row, col, item)
        self._journal_table.scrollToBottom()
        self._fill_journal_lines()

    def _fill_journal_lines(self) -> None:
        """Complete "lines in → out" of the latest entry once counts are known."""
        if not self._journal:
            return
        entry = self._journal[-1]
        if entry.get("lines_out") is not None or not entry.get("outputs"):
            return
        entry["lines_out"] = self._total_lines(entry["outputs"])
        if entry["lines_out"] is None:
            return
        before = "?" if entry["lines_in"] is None else f"{entry['lines_in']:,}"
        item = self._journal_table.item(self._journal_table.rowCount() - 1, 4)
        item.setText(f"{before} → {entry['lines_out']:,} lines")

    def _step_back(self) -> None:
        """Load the file set that was in the list before the last change."""
        if not self._history or self._worker is not None:
            return
        previous = self._history.pop()
        existing = [p for p in previous if p.is_file()]
        self._set_files(existing)
        missing = len(previous) - len(existing)
        note = f" ({missing} no longer exist)" if missing else ""
        self._set_status(f"Stepped back to {len(existing)} file(s){note}")

    def _save_journal(self) -> None:
        start = str(self._files[0].parent / "PyPanTool_journal.txt") if self._files else ""
        name, _ = QFileDialog.getSaveFileName(
            self, "Save journal", start, "Text files (*.txt);;All files (*)"
        )
        if not name:
            return
        header = ("Time (UTC)", "Tool", "Parameters", "Status", "Duration [s]",
                  "Lines in", "Lines out", "Input files", "Output files")
        try:
            with open(name, "w", encoding="utf-8", newline="") as fh:
                fh.write("\t".join(header) + "\r\n")
                for e in self._journal:
                    fh.write("\t".join((
                        e["time"].strftime("%Y-%m-%dT%H:%M:%SZ"), e["label"], e["detail"],
                        e["status"], f"{e['seconds']:.1f}",
                        "" if e["lines_in"] is None else str(e["lines_in"]),
                        "" if e.get("lines_out") is None else str(e["lines_out"]),
                        "; ".join(str(p) for p in e["inputs"]),
                        "; ".join(str(p) for p in e.get("outputs") or []),
                    )) + "\r\n")
        except OSError as exc:
            QMessageBox.warning(self, "Save journal", str(exc))
            return
        self._set_status(f"Journal saved: {Path(name).name}")

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
        self._toolbar.setEnabled(False)

    def set_idle(self, message: str = "Ready") -> None:
        """Return the UI to idle state."""
        self._busy_message = ""
        self._set_status(message)
        self._progress.setVisible(False)
        self._cancel_btn.setVisible(False)
        self.menuBar().setEnabled(True)
        self._toolbar.setEnabled(True)

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

    def attach_worker(
        self, worker: "QThread", label: str = "", detail: str = "", journal: bool = True,
    ) -> None:
        """Register and start a worker; connect generic error, progress and
        cancel handling.  Shows the Cancel button even when the caller did not
        call :meth:`set_busy` before.

        Args:
            worker:  The thread to run.
            label:   Tool name for the journal.
            detail:  Parameters for the journal.
            journal: ``False`` for read-only runs that should not be logged.
        """
        if journal:
            self._pending = {
                "time": datetime.now(UTC), "t0": time.monotonic(),
                "label": label or "Tool", "detail": detail,
                "inputs": list(self._files),
                "lines_in": self._total_lines(self._files),
            }
        self._stop_line_count()
        self._worker = worker
        worker.finished.connect(self._on_worker_finished)
        worker.error.connect(self._on_worker_error)
        if hasattr(worker, "line_progress"):
            worker.line_progress.connect(self._on_line_progress)
        if not self._busy_message:
            self.set_busy("Working…")
        self._refresh_actions()
        worker.start()

    def _on_worker_finished(self) -> None:
        self._worker = None
        self._finish_journal_entry("done")
        self._refresh_actions()
        self._start_line_count()

    def _on_worker_error(self, msg: str) -> None:
        if self._pending is not None:
            self._pending["status"] = "cancelled" if msg == CANCELLED else "failed"
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

    # ── Tool finder (Ctrl+K) ───────────────────────────────────────────────────

    def _find_tool(self) -> None:
        """Type part of a tool name, press Enter to open it."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Find tool")
        dialog.resize(420, 380)
        box = QLineEdit()
        box.setPlaceholderText("Type part of a tool name, Enter to open")
        listing = QListWidget()
        layout = QVBoxLayout(dialog)
        layout.addWidget(box)
        layout.addWidget(listing)
        entries = [
            (f"{group}  ›  {act.text().replace('&', '').rstrip('…')}", act)
            for group, act in self._tool_actions
        ]
        shown: list[QAction] = []

        def refill(text: str) -> None:
            listing.clear()
            shown.clear()
            words = text.lower().split()
            for title, act in entries:
                if all(word in title.lower() for word in words):
                    listing.addItem(title)
                    shown.append(act)
            listing.setCurrentRow(0)

        def choose(*_args) -> None:
            row = listing.currentRow()
            if row < 0:
                return
            act = shown[row]
            dialog.accept()
            if act.isEnabled():
                act.trigger()
            else:
                self._set_status("Load files first to use this tool")

        box.textChanged.connect(refill)
        box.returnPressed.connect(choose)
        listing.itemDoubleClicked.connect(choose)
        refill("")
        dialog.exec()

    # ── Tool action handlers ───────────────────────────────────────────────────

    def _run_stats(self) -> None:
        from gui.run_tool import run_stats
        if self._worker is not None or not self._files:
            return
        path = self._selected_path()
        if path is None:
            QMessageBox.information(
                self, "File statistics", "Select one file in the list first."
            )
            return
        if not path.is_file():
            QMessageBox.warning(self, "File statistics", f"File not found:\n{path}")
            return
        run_stats(self, path)

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

    def _run_convert_datetime(self) -> None:
        from gui.dialogs.datetime_dialog import DateTimeDialog
        DateTimeDialog(self).exec()

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
        OptionsDialog(self).exec()
        # Settings may change how files are read: sniff and peek again.
        self._sniffed.clear()
        self._refresh_actions()
        self._refresh_peek()
        self._start_line_count()

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About PyPanTool",
            "PyPanTool — Data File Swiss Army Knife\n\n"
            "Batch processing of large tabular text files.\n"
            "Inspired by PANGAEA PanTool.",
        )
