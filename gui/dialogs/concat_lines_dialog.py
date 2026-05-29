"""Dialog for Concatenate Files by Lines."""

from functools import partial

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
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

        self._include_filename = QCheckBox("Insert '# filename' before each file's block")
        self._skip_empty = QCheckBox("Skip empty lines")
        self._skip_comments = QCheckBox("Skip comment lines")

        self._comment_prefix = QLineEdit("//")
        self._comment_prefix.setEnabled(False)
        self._skip_comments.toggled.connect(self._comment_prefix.setEnabled)

        form = QFormLayout()
        form.addRow("Skip header lines from files 2..N:", self._skip)
        form.addRow("Comment prefix:", self._comment_prefix)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Append all loaded files top-to-bottom into one output file."))
        layout.addLayout(form)
        layout.addWidget(self._include_filename)
        layout.addWidget(self._skip_empty)
        layout.addWidget(self._skip_comments)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        self.accept()
        fn = partial(
            concat_by_lines,
            skip_header_lines=self._skip.value(),
            include_filename=self._include_filename.isChecked(),
            skip_empty=self._skip_empty.isChecked(),
            skip_comments=self._skip_comments.isChecked(),
            comment_prefix=self._comment_prefix.text() or "//",
        )
        run_concat(self._mw, fn, "Concat by lines")
