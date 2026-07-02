"""Dialog for Search One String (match report across all loaded files)."""

from functools import partial

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.search_replace import search_one_string
from gui.run_tool import run_concat


class SearchOneDialog(QDialog):
    """Collect a search string and line window, then write a match report."""

    def __init__(self, main_window, parent: QWidget | None = None) -> None:
        super().__init__(parent or main_window)
        self._mw = main_window

        self.setWindowTitle("Search One String")
        self.setMinimumWidth(380)

        self._search = QLineEdit()

        self._start_line = QSpinBox()
        self._start_line.setRange(1, 2_000_000_000)
        self._start_line.setValue(1)

        self._num_lines = QSpinBox()
        self._num_lines.setRange(0, 2_000_000_000)
        self._num_lines.setValue(0)
        self._num_lines.setSpecialValueText("all")

        form = QFormLayout()
        form.addRow("Search for:", self._search)
        form.addRow("Start at line:", self._start_line)
        form.addRow("Number of lines:", self._num_lines)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Writes a report of every match in all loaded files:\n"
            "one row per match with filename, line number, and the line."
        ))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        search = self._search.text()
        if not search:
            QMessageBox.warning(self, "Input required", "Please enter a search string.")
            return

        settings = self._mw.current_settings()
        delimiter = settings.get("delimiter", "\t")

        self.accept()
        run_concat(
            self._mw,
            partial(
                search_one_string,
                search=search,
                start_line=self._start_line.value(),
                num_lines=self._num_lines.value(),
                delimiter=delimiter,
            ),
            "Search one string",
            min_files=1,
        )
