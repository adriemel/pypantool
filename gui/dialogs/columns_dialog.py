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

from core.columns import delete_columns, extract_columns, parse_column_spec
from gui.options_dialog import table_options
from gui.peek import header_and_first_row
from gui.run_tool import run_tool
from gui.style import AMBER, TEAL


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

        # Header of the first loaded file, to show what the spec selects.
        settings = main_window.current_settings()
        options = table_options(settings)
        sample = header_and_first_row(
            main_window.files[0], settings["in_encoding"], options
        )
        self._names = sample[0].split(options["delimiter"]) if sample else []
        self._resolved = QLabel()
        self._resolved.setWordWrap(True)
        self._spec.textChanged.connect(self._update_resolved)

        form = QFormLayout()
        form.addRow(f"Columns to {action}:", self._spec)
        form.addRow("", self._resolved)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(verb)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Enter column numbers or ranges (comma-separated, 1-based).\n"
            "Use <b>end</b> for the last column, e.g. <tt>3-end</tt>."
        ))
        layout.addLayout(form)
        layout.addWidget(buttons)
        self._update_resolved()

    def _update_resolved(self) -> None:
        """Show which columns of the first file the spec selects."""
        total = len(self._names)
        spec = self._spec.text().strip()
        if not total:
            self._resolved.setText("")
            return
        if not spec:
            self._resolved.setStyleSheet("")
            self._resolved.setText(
                f"{total} columns in {self._mw.files[0].name}: "
                + _listing(self._names, range(total))
            )
            return
        try:
            indices = parse_column_spec(spec, total)
        except ValueError as exc:
            self._resolved.setStyleSheet(f"color: {AMBER};")
            self._resolved.setText(str(exc))
            return
        word = "Keeps" if self._mode == "extract" else "Removes"
        self._resolved.setStyleSheet(f"color: {TEAL};")
        self._resolved.setText(
            f"{word} {len(indices)} of {total}: " + _listing(self._names, indices)
        )

    def _accept(self) -> None:
        spec = self._spec.text().strip()
        if not spec:
            QMessageBox.warning(self, "Input required", "Please enter a column spec.")
            return

        settings = self._mw.current_settings()
        fn = extract_columns if self._mode == "extract" else delete_columns
        label = "Extract columns" if self._mode == "extract" else "Delete columns"

        self.accept()
        run_tool(self._mw, partial(fn, spec=spec, **table_options(settings)), label)


def _listing(names: list[str], indices, limit: int = 8) -> str:
    """Numbered column names, shortened after *limit* entries."""
    picked = [f"{i + 1} {names[i]}" for i in indices]
    if len(picked) > limit:
        picked = picked[:limit] + [f"… ({len(picked) - limit} more)"]
    return "  ·  ".join(picked)
