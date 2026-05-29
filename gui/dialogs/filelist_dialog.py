"""Dialog for Save File List."""

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from gui.run_tool import run_filelist


class FilelistDialog(QDialog):
    """Confirm and export metadata for all loaded files to one output file."""

    def __init__(self, main_window, parent: QWidget | None = None) -> None:
        super().__init__(parent or main_window)
        self._mw = main_window
        self.setWindowTitle("Save File List")
        self.setMinimumWidth(340)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Export metadata for all loaded files to a single output file.\n"
            "Columns: Name, Path, Size (bytes), Modified."
        ))
        layout.addWidget(buttons)

    def _accept(self) -> None:
        self.accept()
        run_filelist(self._mw)
