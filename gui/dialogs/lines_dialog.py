"""Dialog for Extract Lines / Delete Lines (by line number or range)."""

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

from core.lines import delete_lines, extract_lines
from gui.run_tool import run_tool


class LinesDialog(QDialog):
    """Collect a line-number spec and run extract or delete."""

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
        self.setWindowTitle(f"{verb} Lines")
        self.setMinimumWidth(340)

        action = "keep" if mode == "extract" else "remove"
        self._spec = QLineEdit()
        self._spec.setPlaceholderText("e.g. 1-3, 5, 10-end")

        form = QFormLayout()
        form.addRow(f"Lines to {action}:", self._spec)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Enter line numbers or ranges (comma-separated).\n"
            "Use <b>end</b> for the last line, e.g. <tt>5-end</tt>."
        ))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        spec = self._spec.text().strip()
        if not spec:
            QMessageBox.warning(self, "Input required", "Please enter a line spec.")
            return

        fn = extract_lines if self._mode == "extract" else delete_lines
        label = "Extract lines" if self._mode == "extract" else "Delete lines"

        self.accept()
        run_tool(self._mw, partial(fn, spec=spec), label)
