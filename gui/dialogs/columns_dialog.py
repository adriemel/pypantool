"""Dialog for Extract Columns / Delete Columns (by number or range)."""

from functools import partial

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from core.columns import delete_columns, extract_columns
from gui.run_tool import run_tool


class ColumnsDialog(QDialog):
    """Collect a column-number spec and run extract or delete."""

    def __init__(self, main_window, mode: str, parent: QWidget | None = None) -> None:
        """
        Args:
            main_window: The :class:`~gui.main_window.MainWindow` instance.
            mode:        ``"extract"`` or ``"delete"``.
        """
        super().__init__(parent or main_window)
        self._mw = main_window
        self._mode = mode

        verb = "Extract" if mode == "extract" else "Delete"
        self.setWindowTitle(f"{verb} Columns")
        self.setMinimumWidth(360)

        action = "keep" if mode == "extract" else "remove"
        self._spec = QLineEdit()
        self._spec.setPlaceholderText("e.g. 1-3, 5, 7-end")

        form = QFormLayout()
        form.addRow(f"Columns to {action}:", self._spec)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Enter column numbers or ranges (comma-separated, 1-based).\n"
            "Use <b>end</b> for the last column, e.g. <tt>3-end</tt>."
        ))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        spec = self._spec.text().strip()
        if not spec:
            QMessageBox.warning(self, "Input required", "Please enter a column spec.")
            return

        settings = self._mw.current_settings()
        delimiter = settings["delimiter"]
        fn = extract_columns if self._mode == "extract" else delete_columns
        label = "Extract columns" if self._mode == "extract" else "Delete columns"

        self.accept()
        run_tool(self._mw, partial(fn, spec=spec, delimiter=delimiter), label)
