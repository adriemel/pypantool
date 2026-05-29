"""Dialog for Search and Replace One String."""

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

from core.search_replace import search_replace_one
from gui.run_tool import run_tool


class SearchReplaceDialog(QDialog):
    """Collect a search/replace pair and apply it to all loaded files."""

    def __init__(self, main_window, parent: QWidget | None = None) -> None:
        super().__init__(parent or main_window)
        self._mw = main_window
        self.setWindowTitle("Search and Replace")
        self.setMinimumWidth(400)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Text to find")
        self._replace = QLineEdit()
        self._replace.setPlaceholderText("Replacement text (leave empty to delete)")

        form = QFormLayout()
        form.addRow("Search:", self._search)
        form.addRow("Replace:", self._replace)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Replace all occurrences of the search text in every loaded file."))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        search = self._search.text()
        if not search:
            QMessageBox.warning(self, "Input required", "Please enter a search string.")
            return
        self.accept()
        run_tool(
            self._mw,
            partial(search_replace_one, search=search, replace=self._replace.text()),
            "Search and replace",
        )
