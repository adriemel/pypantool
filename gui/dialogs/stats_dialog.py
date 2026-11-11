"""Statistics window for one file (result of core.profile.profile_lines)."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.naming import unique_path
from core.profile import COLUMN_HEADERS, TableProfile, column_rows, format_profile, summary_rows

_ATTENTION = QColor("#A85A00")
_ATTENTION_BG = QColor("#FFF4E0")
# Columns of COLUMN_HEADERS shown right-aligned (counts and numbers).
_RIGHT = {0, 3, 4, 5, 6, 7, 8, 9}


class StatsDialog(QDialog):
    """Show file summary and per-column statistics; optionally save a report."""

    def __init__(
        self,
        main_window,
        path: Path,
        profile: TableProfile,
        settings: dict,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent or main_window)
        self._path = path
        self._profile = profile
        self._settings = settings
        self.setWindowTitle(f"File statistics — {path.name}")
        self.resize(1280, 560)

        form = QFormLayout()
        form.setVerticalSpacing(3)
        for label, text, attention in summary_rows(profile, settings["in_encoding"]):
            value = QLabel(text)
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            if attention:
                value.setStyleSheet(f"color: {_ATTENTION.name()}; font-weight: bold;")
            form.addRow(f"{label}:", value)

        rows = column_rows(profile)
        table = QTableWidget(len(rows), len(COLUMN_HEADERS))
        table.setHorizontalHeaderLabels(COLUMN_HEADERS)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(24)
        for r, (cells, attention) in enumerate(rows):
            for c, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                if c in _RIGHT:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                if attention and c >= len(COLUMN_HEADERS) - 2 and text:
                    item.setForeground(_ATTENTION)
                    item.setBackground(_ATTENTION_BG)
                table.setItem(r, c, item)
        # Size columns to their content once, then let the user drag them.
        table.resizeColumnsToContents()
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        for c in range(len(COLUMN_HEADERS) - 1):
            table.setColumnWidth(c, min(table.columnWidth(c) + 8, 260))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        save = buttons.addButton("Save report…", QDialogButtonBox.ButtonRole.ActionRole)
        save.clicked.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(table, 1)
        layout.addWidget(buttons)

    def _save(self) -> None:
        out_path = unique_path(self._path.parent, f"{self._path.stem}_stats", ".txt")
        lines = format_profile(
            self._profile, self._path.name, self._settings["in_encoding"]
        )
        try:
            with open(out_path, "w", encoding=self._settings["out_encoding"],
                      errors="replace", newline="") as fh:
                for line in lines:
                    fh.write(line + "\r\n")
        except OSError as exc:
            QMessageBox.warning(self, "Save report", str(exc))
            return
        QMessageBox.information(
            self, "Save report", f"Report written to:\n{out_path}"
        )
