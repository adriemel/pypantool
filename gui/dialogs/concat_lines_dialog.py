"""Dialog for Concatenate Files by Lines."""

from functools import partial

from PySide6.QtWidgets import (
    QCheckBox,
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

from core.concat import concat_by_lines
from gui.run_tool import run_concat


class ConcatLinesDialog(QDialog):
    """Collect options and run concatenation by lines on all loaded files."""

    def __init__(self, main_window, parent: QWidget | None = None) -> None:
        super().__init__(parent or main_window)
        self._mw = main_window
        self.setWindowTitle("Concatenate Files by Lines")
        self.setMinimumWidth(360)

        self._skip = QSpinBox()
        self._skip.setRange(0, 9999)
        self._skip.setValue(0)
        self._skip.setToolTip("Lines to skip from files 2..N (e.g. 1 to drop duplicate headers)")

        self._filename_column = QCheckBox(
            "Add filename (without extension) as column 1"
        )
        self._filename_column.setToolTip(
            "Every data line gets its file's name as first column. The last header\n"
            "line of the first file gets 'Filename'. Comment and empty lines are\n"
            "left unchanged."
        )
        self._skip_empty = QCheckBox("Skip empty lines")
        self._skip_comments = QCheckBox("Skip comment lines")
        self._trash_inputs = QCheckBox("Move input files to recycle bin afterwards")
        self._trash_inputs.setToolTip(
            "Only after the concatenated file was written successfully."
        )

        # The prefix is used both for skipping comments and for leaving comment
        # lines unprefixed in the filename column.
        self._comment_prefix = QLineEdit("//")
        self._comment_prefix.setEnabled(False)
        self._skip_comments.toggled.connect(self._update_prefix_enabled)
        self._filename_column.toggled.connect(self._update_prefix_enabled)

        form = QFormLayout()
        form.addRow("Header lines (kept once, skipped from files 2..N):", self._skip)
        form.addRow("Comment prefix:", self._comment_prefix)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Append all loaded files top-to-bottom into Concatenate_out.<ext>\n"
            "in the folder of the first file."
        ))
        layout.addLayout(form)
        layout.addWidget(self._filename_column)
        layout.addWidget(self._skip_empty)
        layout.addWidget(self._skip_comments)
        layout.addWidget(self._trash_inputs)
        layout.addWidget(buttons)

    def _update_prefix_enabled(self) -> None:
        self._comment_prefix.setEnabled(
            self._skip_comments.isChecked() or self._filename_column.isChecked()
        )

    def _accept(self) -> None:
        trash = self._trash_inputs.isChecked()
        if trash:
            answer = QMessageBox.question(
                self, "Move input files to recycle bin",
                f"After concatenation, the {len(self._mw.files)} input file(s) "
                "will be moved to the recycle bin. Continue?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        settings = self._mw.current_settings()
        self.accept()
        fn = partial(
            concat_by_lines,
            skip_header_lines=self._skip.value(),
            filename_column=self._filename_column.isChecked(),
            skip_empty=self._skip_empty.isChecked(),
            skip_comments=self._skip_comments.isChecked(),
            comment_prefix=self._comment_prefix.text() or "//",
            delimiter=settings.get("delimiter", "\t"),
        )
        run_concat(
            self._mw, fn, "Concat by lines",
            out_stem="Concatenate_out",
            trash_inputs=trash,
        )
