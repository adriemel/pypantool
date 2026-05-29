"""Dialog for Extract Matched Lines / Delete Matched Lines."""

from functools import partial

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from core.lines import delete_matched_lines, extract_matched_lines
from gui.run_tool import run_tool


class MatchedLinesDialog(QDialog):
    """Collect a search pattern and run extract-matched or delete-matched."""

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
        self.setWindowTitle(f"{verb} Matched Lines")
        self.setMinimumWidth(360)

        action = "keep" if mode == "extract" else "remove"
        self._pattern = QLineEdit()
        self._pattern.setPlaceholderText("Search string or regex")
        self._is_regex = QCheckBox("Use regular expression")

        form = QFormLayout()
        form.addRow(f"Pattern ({action} matching lines):", self._pattern)
        form.addRow("", self._is_regex)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Lines containing the pattern will be "
            + ("kept." if mode == "extract" else "removed.")
        ))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        pattern = self._pattern.text()
        if not pattern:
            QMessageBox.warning(self, "Input required", "Please enter a search pattern.")
            return

        fn = extract_matched_lines if self._mode == "extract" else delete_matched_lines
        label = (
            "Extract matched lines" if self._mode == "extract" else "Delete matched lines"
        )

        self.accept()
        run_tool(
            self._mw,
            partial(fn, pattern=pattern, is_regex=self._is_regex.isChecked()),
            label,
        )
