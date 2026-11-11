"""Options dialog — naming pattern, encoding, delimiter, header line, comment prefix.

Settings are persisted via QSettings under the key group "PyPanTool".
"""

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_PATTERN = "%N_out%E"
DEFAULT_IN_ENCODING = "UTF-8"
DEFAULT_OUT_ENCODING = "UTF-8"
DEFAULT_DELIMITER = "\t"
DEFAULT_HEADER_LINE = 1
DEFAULT_COMMENT_PREFIX = "//"

_ENCODINGS = ["UTF-8", "Latin-1", "CP1252", "ASCII"]
_DELIMITERS = [("Tab (\\t)", "\t"), ("Semicolon (;)", ";"), ("Comma (,)", ","),
               ("Pipe (|)", "|"), ("Space ( )", " ")]


# ── Settings helpers ───────────────────────────────────────────────────────────

def load_settings() -> dict:
    """Return the current application settings as a plain dict."""
    s = QSettings("PyPanTool", "PyPanTool")
    return {
        "pattern": s.value("pattern", DEFAULT_PATTERN),
        "in_encoding": s.value("in_encoding", DEFAULT_IN_ENCODING),
        "out_encoding": s.value("out_encoding", DEFAULT_OUT_ENCODING),
        "delimiter": s.value("delimiter", DEFAULT_DELIMITER),
        "header_line": int(s.value("header_line", DEFAULT_HEADER_LINE)),
        "comment_prefix": s.value("comment_prefix", DEFAULT_COMMENT_PREFIX),
    }


def table_options(settings: dict) -> dict:
    """Keyword arguments shared by every column-aware core tool."""
    return {
        "delimiter": settings["delimiter"],
        "header_line": settings["header_line"],
        "comment_prefix": settings["comment_prefix"],
    }


def save_settings(settings: dict) -> None:
    """Persist *settings* dict to QSettings."""
    s = QSettings("PyPanTool", "PyPanTool")
    s.setValue("pattern", settings["pattern"])
    s.setValue("in_encoding", settings["in_encoding"])
    s.setValue("out_encoding", settings["out_encoding"])
    s.setValue("delimiter", settings["delimiter"])
    s.setValue("header_line", settings["header_line"])
    s.setValue("comment_prefix", settings["comment_prefix"])


# ── Dialog ─────────────────────────────────────────────────────────────────────

class OptionsDialog(QDialog):
    """Modal dialog for application-wide options."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Options")
        self.setMinimumWidth(360)

        current = load_settings()

        # Pattern
        self._pattern = QLineEdit(current["pattern"])

        # Encodings
        self._in_enc = QComboBox()
        self._in_enc.addItems(_ENCODINGS)
        self._in_enc.setCurrentText(current["in_encoding"])

        self._out_enc = QComboBox()
        self._out_enc.addItems(_ENCODINGS)
        self._out_enc.setCurrentText(current["out_encoding"])

        # Delimiter
        self._delim = QComboBox()
        for label, _ in _DELIMITERS:
            self._delim.addItem(label)
        current_delim = current["delimiter"]
        for i, (_, val) in enumerate(_DELIMITERS):
            if val == current_delim:
                self._delim.setCurrentIndex(i)
                break

        # Header line / comment prefix (shared by all column-aware tools)
        self._header_line = QSpinBox()
        self._header_line.setRange(1, 1_000_000)
        self._header_line.setValue(current["header_line"])
        self._header_line.setToolTip(
            "Earliest line the column header can be on. Lines before it are\n"
            "copied unchanged by all column tools. A leading /* ... */ block\n"
            "(PANGAEA download) is skipped automatically."
        )
        self._comment_prefix = QLineEdit(current["comment_prefix"])
        self._comment_prefix.setToolTip(
            "Lines starting with this text are never treated as header or data\n"
            "by the column tools."
        )

        form = QFormLayout()
        form.addRow("Output name pattern:", self._pattern)
        form.addRow("Input encoding:", self._in_enc)
        form.addRow("Output encoding:", self._out_enc)
        form.addRow("Column delimiter:", self._delim)
        form.addRow("Header is on or after line:", self._header_line)
        form.addRow("Comment prefix:", self._comment_prefix)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _accept(self) -> None:
        delimiter_value = _DELIMITERS[self._delim.currentIndex()][1]
        save_settings({
            "pattern": self._pattern.text().strip() or DEFAULT_PATTERN,
            "in_encoding": self._in_enc.currentText(),
            "out_encoding": self._out_enc.currentText(),
            "delimiter": delimiter_value,
            "header_line": self._header_line.value(),
            "comment_prefix": self._comment_prefix.text(),
        })
        self.accept()
