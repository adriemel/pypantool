"""Dialog for Insert/Replace Characters at Positions."""

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

from core.charpos import insert_at_positions, parse_positions, replace_at_positions
from gui.run_tool import run_tool


class CharPosDialog(QDialog):
    """Collect character positions and text, then run insert or replace."""

    def __init__(self, main_window, mode: str, parent: QWidget | None = None) -> None:
        """
        Args:
            main_window: The :class:`~gui.main_window.MainWindow` instance.
            mode:        ``"insert"`` or ``"replace"``.
        """
        super().__init__(parent or main_window)
        self._mw = main_window
        self._mode = mode

        verb = "Insert" if mode == "insert" else "Replace"
        self.setWindowTitle(f"{verb} Characters at Positions")
        self.setMinimumWidth(380)

        self._spec = QLineEdit()
        self._spec.setPlaceholderText("e.g. 5, 10-12")

        self._text = QLineEdit()
        self._text.setPlaceholderText("^t = tab")

        form = QFormLayout()
        form.addRow("Character positions:", self._spec)
        label = "Text to insert:" if mode == "insert" else "Replacement text:"
        form.addRow(label, self._text)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        explain = (
            "Inserts the text before each character position (1-based)."
            if mode == "insert"
            else "Replaces the character at each position (1-based) with the text.\n"
                 "Leave the text empty to delete those characters."
        )
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(explain))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        spec = self._spec.text().strip()
        text = self._text.text().replace("^t", "\t")

        try:
            parse_positions(spec)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid positions", str(exc))
            return
        if self._mode == "insert" and not text:
            QMessageBox.warning(self, "Input required", "Please enter text to insert.")
            return

        fn = insert_at_positions if self._mode == "insert" else replace_at_positions
        label = ("Insert" if self._mode == "insert" else "Replace") + " characters"

        self.accept()
        run_tool(self._mw, partial(fn, spec=spec, text=text), label)
