"""Dialog for Search and Replace Many Strings (database file)."""

from functools import partial
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.search_replace import load_replacements, search_replace_many
from gui.run_tool import run_tool


class SearchReplaceManyDialog(QDialog):
    """Select a replacement-database file and apply all pairs to loaded files."""

    def __init__(self, main_window, parent: QWidget | None = None) -> None:
        super().__init__(parent or main_window)
        self._mw = main_window
        self.setWindowTitle("Search and Replace Many")
        self.setMinimumWidth(480)

        self._db_path = QLineEdit()
        self._db_path.setPlaceholderText("Path to replacement database file…")
        self._db_path.setReadOnly(True)

        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)

        path_row = QHBoxLayout()
        path_row.addWidget(self._db_path, 1)
        path_row.addWidget(browse_btn)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Select a tab-delimited database file where the first column is the\n"
            "search text and the second column is the replacement text.\n"
            "All pairs are applied in file order to every loaded file."
        ))
        layout.addLayout(path_row)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select replacement database", "", "Text files (*.txt *.tab *.tsv);;All files (*)"
        )
        if path:
            self._db_path.setText(path)

    def _accept(self) -> None:
        path_str = self._db_path.text().strip()
        if not path_str:
            QMessageBox.warning(self, "Input required", "Please select a database file.")
            return

        db_path = Path(path_str)
        if not db_path.is_file():
            QMessageBox.warning(self, "File not found", f"Cannot open:\n{db_path}")
            return

        settings = self._mw.current_settings()
        delimiter = settings.get("delimiter", "\t")

        try:
            with open(db_path, encoding=settings["in_encoding"], errors="replace") as fh:
                lines = [line.rstrip("\n") for line in fh]
            replacements = load_replacements(lines, delimiter=delimiter)
        except OSError as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return

        if not replacements:
            QMessageBox.warning(
                self, "Empty database",
                "No valid search/replace pairs found in the database file."
            )
            return

        self.accept()
        run_tool(
            self._mw,
            partial(search_replace_many, replacements=replacements),
            f"Search and replace ({len(replacements)} pairs)",
        )
