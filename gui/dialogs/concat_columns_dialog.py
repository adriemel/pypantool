"""Dialog for Concatenate Files by Columns."""

from functools import partial

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.concat import concat_by_columns
from gui.run_tool import run_concat


class ConcatColumnsDialog(QDialog):
    """Collect options and run side-by-side column merge on all loaded files."""

    def __init__(self, main_window, parent: QWidget | None = None) -> None:
        super().__init__(parent or main_window)
        self._mw = main_window
        self.setWindowTitle("Concatenate Files by Columns")
        self.setMinimumWidth(360)

        self._skip = QSpinBox()
        self._skip.setRange(0, 9999)
        self._skip.setValue(0)
        self._skip.setToolTip("Lines to skip from the top of every file before zipping")

        self._include_filename_row = QCheckBox(
            "Prepend a row of filenames as the first output row"
        )

        form = QFormLayout()
        form.addRow("Skip header lines (all files):", self._skip)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Merge all loaded files side-by-side into one output file.\n"
                "All files must have the same number of rows."
            )
        )
        layout.addLayout(form)
        layout.addWidget(self._include_filename_row)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        self.accept()
        settings = self._mw.current_settings()
        delimiter = settings.get("delimiter", "\t")
        fn = partial(
            concat_by_columns,
            delimiter=delimiter,
            skip_header_lines=self._skip.value(),
            include_filename_row=self._include_filename_row.isChecked(),
        )
        run_concat(self._mw, fn, "Concat by columns")
