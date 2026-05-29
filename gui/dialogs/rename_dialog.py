"""Dialog for bulk file rename."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.rename import preview_renames


class RenameDialog(QDialog):
    """Collect rename parameters and show a live preview of old → new filenames."""

    def __init__(self, main_window, parent: QWidget | None = None) -> None:
        super().__init__(parent or main_window)
        self._mw = main_window
        self.setWindowTitle("Rename Files")
        self.setMinimumWidth(540)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Text to find in filename")
        self._replace = QLineEdit()
        self._replace.setPlaceholderText("Replacement (leave empty to delete found text)")
        self._prefix = QLineEdit()
        self._prefix.setPlaceholderText("Text added before filename")
        self._suffix = QLineEdit()
        self._suffix.setPlaceholderText("Text inserted after stem, before extension")

        for field in (self._search, self._replace, self._prefix, self._suffix):
            field.textChanged.connect(self._update_preview)

        form = QFormLayout()
        form.addRow("Search:", self._search)
        form.addRow("Replace:", self._replace)
        form.addRow("Prefix:", self._prefix)
        form.addRow("Suffix:", self._suffix)

        self._preview_table = QTableWidget(0, 2)
        self._preview_table.setHorizontalHeaderLabels(["Current name", "New name"])
        self._preview_table.horizontalHeader().setStretchLastSection(True)
        self._preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._preview_table.setAlternatingRowColors(True)
        self._preview_table.verticalHeader().setVisible(False)
        self._preview_table.verticalHeader().setDefaultSectionSize(22)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setEnabled(False)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Rename all loaded files. Operations are applied in order: search/replace → prefix → suffix."))
        layout.addLayout(form)
        layout.addWidget(QLabel("Preview:"))
        layout.addWidget(self._preview_table)
        layout.addWidget(buttons)

        self._update_preview()

    def _update_preview(self) -> None:
        params = self._params()
        pairs = preview_renames(self._mw.files, **params)
        self._preview_table.setRowCount(len(pairs))
        has_change = False
        for row, (old_path, new_path) in enumerate(pairs):
            old_item = QTableWidgetItem(old_path.name)
            new_item = QTableWidgetItem(new_path.name)
            if old_path.name != new_path.name:
                new_item.setForeground(Qt.GlobalColor.darkGreen)
                has_change = True
            self._preview_table.setItem(row, 0, old_item)
            self._preview_table.setItem(row, 1, new_item)
        self._preview_table.resizeColumnToContents(0)
        self._ok_button.setEnabled(has_change)

    def _params(self) -> dict:
        return {
            "search": self._search.text(),
            "replace": self._replace.text(),
            "prefix": self._prefix.text(),
            "suffix": self._suffix.text(),
        }

    def _accept(self) -> None:
        from gui.run_tool import run_rename
        params = self._params()
        self.accept()
        run_rename(self._mw, **params)
