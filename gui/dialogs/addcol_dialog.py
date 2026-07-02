"""Dialog for Add Column (constant text and/or metadata columns)."""

from functools import partial

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from core.addcol import add_column
from gui.run_tool import run_tool


class AddColumnDialog(QDialog):
    """Collect column text and metadata options, then add columns to all files."""

    def __init__(self, main_window, parent: QWidget | None = None) -> None:
        super().__init__(parent or main_window)
        self._mw = main_window

        self.setWindowTitle("Add Column")
        self.setMinimumWidth(400)

        # ── User column ────────────────────────────────────────────────────────
        self._header_text = QLineEdit()
        self._header_text.setPlaceholderText("Header cell (first line)")
        self._column_text = QLineEdit()
        self._column_text.setPlaceholderText("Value repeated on every data line")

        self._col_prepend = QRadioButton("Prepend")
        self._col_append = QRadioButton("Append")
        self._col_append.setChecked(True)
        col_pos = QHBoxLayout()
        col_pos.addWidget(self._col_prepend)
        col_pos.addWidget(self._col_append)
        col_pos.addStretch()

        col_form = QFormLayout()
        col_form.addRow("Header text:", self._header_text)
        col_form.addRow("Column text:", self._column_text)
        col_form.addRow("Position:", col_pos)

        col_group = QGroupBox("Text column")
        col_group.setLayout(col_form)

        # ── Metadata columns ───────────────────────────────────────────────────
        self._meta_filename = QCheckBox("Filename without extension (header: Event label)")
        self._meta_fullpath = QCheckBox("Full file path (header: Filename)")
        self._meta_ordinal = QCheckBox("Line number (header: No)")

        self._meta_prepend = QRadioButton("Prepend")
        self._meta_append = QRadioButton("Append")
        self._meta_prepend.setChecked(True)
        meta_pos = QHBoxLayout()
        meta_pos.addWidget(self._meta_prepend)
        meta_pos.addWidget(self._meta_append)
        meta_pos.addStretch()

        meta_form = QFormLayout()
        meta_form.addRow(self._meta_filename)
        meta_form.addRow(self._meta_fullpath)
        meta_form.addRow(self._meta_ordinal)
        meta_form.addRow("Position:", meta_pos)

        meta_group = QGroupBox("Metadata columns")
        meta_group.setLayout(meta_form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(col_group)
        layout.addWidget(meta_group)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        header_text = self._header_text.text().replace("^t", "\t")
        column_text = self._column_text.text().replace("^t", "\t")

        add_filename = self._meta_filename.isChecked()
        add_full_path = self._meta_fullpath.isChecked()
        add_ordinal = self._meta_ordinal.isChecked()

        if not (header_text or column_text or add_filename or add_full_path or add_ordinal):
            QMessageBox.warning(
                self, "Input required",
                "Enter column text or select at least one metadata column.",
            )
            return

        settings = self._mw.current_settings()
        delimiter = settings.get("delimiter", "\t")

        self.accept()
        run_tool(
            self._mw,
            partial(
                add_column,
                header_text=header_text,
                column_text=column_text,
                position="prepend" if self._col_prepend.isChecked() else "append",
                add_filename=add_filename,
                add_full_path=add_full_path,
                add_ordinal=add_ordinal,
                meta_position="prepend" if self._meta_prepend.isChecked() else "append",
                delimiter=delimiter,
            ),
            "Add column",
            pass_path=True,
        )
