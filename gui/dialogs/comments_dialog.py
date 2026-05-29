"""Dialog for Delete Comment Blocks."""

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

from core.comments import delete_comments
from gui.run_tool import run_tool


class CommentsDialog(QDialog):
    """Collect a comment prefix and remove all matching lines."""

    def __init__(self, main_window, parent: QWidget | None = None) -> None:
        super().__init__(parent or main_window)
        self._mw = main_window
        self.setWindowTitle("Delete Comment Blocks")
        self.setMinimumWidth(320)

        self._prefix = QLineEdit("//")

        form = QFormLayout()
        form.addRow("Comment prefix:", self._prefix)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Remove all lines that start with the given prefix."))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        prefix = self._prefix.text()
        if not prefix:
            QMessageBox.warning(self, "Input required", "Please enter a comment prefix.")
            return
        self.accept()
        run_tool(self._mw, partial(delete_comments, prefix=prefix), "Delete comments")
