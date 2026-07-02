"""Dialog for Add Text Line / Add Text Block (insert at a line number)."""

from functools import partial

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.addline import add_lines
from gui.run_tool import run_tool


class AddLineDialog(QDialog):
    """Collect text and a line number, then insert into all files."""

    def __init__(self, main_window, mode: str, parent: QWidget | None = None) -> None:
        """
        Args:
            main_window: The :class:`~gui.main_window.MainWindow` instance.
            mode:        ``"line"`` (single line) or ``"block"`` (multi-line).
        """
        super().__init__(parent or main_window)
        self._mw = main_window
        self._mode = mode

        title = "Add Text Line" if mode == "line" else "Add Text Block"
        self.setWindowTitle(title)
        self.setMinimumWidth(400)

        self._line_edit: QLineEdit | None = None
        self._block_edit: QPlainTextEdit | None = None

        self._line_no = QSpinBox()
        self._line_no.setRange(1, 2_000_000_000)
        self._line_no.setValue(1)

        form = QFormLayout()
        if mode == "line":
            self._line_edit = QLineEdit()
            self._line_edit.setPlaceholderText("^t = tab")
            form.addRow("Text line:", self._line_edit)
        else:
            self._block_edit = QPlainTextEdit()
            self._block_edit.setPlaceholderText("One line per row; ^t = tab")
            self._block_edit.setTabChangesFocus(True)
            self._block_edit.setMinimumHeight(120)
            form.addRow("Text block:", self._block_edit)
        form.addRow("Insert at line number:", self._line_no)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "The text is inserted before the current line at that position.\n"
            "If the file is shorter, the text is appended at the end."
        ))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        if self._mode == "line":
            raw = self._line_edit.text()
            text_lines = [raw.replace("^t", "\t")] if raw else []
        else:
            raw = self._block_edit.toPlainText()
            text_lines = [l.replace("^t", "\t") for l in raw.split("\n")] if raw else []

        if not text_lines:
            QMessageBox.warning(self, "Input required", "Please enter text to insert.")
            return

        label = "Add text line" if self._mode == "line" else "Add text block"

        self.accept()
        run_tool(
            self._mw,
            partial(add_lines, text_lines=text_lines, line_no=self._line_no.value()),
            label,
        )
