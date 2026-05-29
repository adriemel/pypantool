"""Dialog for column recalculation."""

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

from core.recalc import recalculate_columns
from gui.run_tool import run_tool

_DELIM_NAMES = {"\t": "tab", ";": "semicolon", ",": "comma", "|": "pipe", " ": "space"}


class RecalcDialog(QDialog):
    """Collect column spec, factor, and offset, then recalculate across all loaded files."""

    def __init__(self, main_window, parent: QWidget | None = None) -> None:
        super().__init__(parent or main_window)
        self._mw = main_window
        self.setWindowTitle("Recalculate Columns")
        self.setMinimumWidth(380)

        settings = main_window.current_settings()
        self._delimiter = settings.get("delimiter", "\t")
        delim_name = _DELIM_NAMES.get(self._delimiter, repr(self._delimiter))

        self._spec = QLineEdit()
        self._spec.setPlaceholderText("e.g.  4  or  2,4  or  3-5")
        self._factor = QLineEdit("1")
        self._offset = QLineEdit("0")
        self._header_lines = QSpinBox()
        self._header_lines.setRange(0, 999)
        self._header_lines.setValue(0)

        form = QFormLayout()
        form.addRow("Columns (1-based):", self._spec)
        form.addRow("Factor (multiply by):", self._factor)
        form.addRow("Offset (add):", self._offset)
        form.addRow("Header lines to skip:", self._header_lines)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Apply  new = old × factor + offset  to the selected columns.\nDelimiter: {delim_name}"))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        spec = self._spec.text().strip()
        if not spec:
            QMessageBox.warning(self, "Input required", "Please enter a column spec.")
            return
        try:
            factor = float(self._factor.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid input", "Factor must be a number.")
            return
        try:
            offset = float(self._offset.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid input", "Offset must be a number.")
            return

        self.accept()
        run_tool(
            self._mw,
            partial(
                recalculate_columns,
                spec=spec,
                factor=factor,
                offset=offset,
                delimiter=self._delimiter,
                header_lines=self._header_lines.value(),
            ),
            "Recalculate columns",
        )
