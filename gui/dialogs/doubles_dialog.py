"""Dialog for Delete Double Lines."""

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from core.duplicates import delete_double_lines
from gui.run_tool import run_tool


class DoublesDialog(QDialog):
    """Confirm and run duplicate-line removal on all loaded files."""

    def __init__(self, main_window, parent: QWidget | None = None) -> None:
        super().__init__(parent or main_window)
        self._mw = main_window
        self.setWindowTitle("Delete Double Lines")
        self.setMinimumWidth(320)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Remove duplicate lines from all loaded files.\n"
                "The first occurrence of each line is kept."
            )
        )
        layout.addWidget(buttons)

    def _accept(self) -> None:
        self.accept()
        run_tool(self._mw, delete_double_lines, "Delete double lines")
