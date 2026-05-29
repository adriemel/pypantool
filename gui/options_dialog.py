"""Options dialog — naming pattern, encoding, delimiter.

Settings are persisted via QSettings under the key group "PyPanTool".
"""

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_PATTERN = "%N_out%E"
DEFAULT_IN_ENCODING = "UTF-8"
DEFAULT_OUT_ENCODING = "UTF-8"
DEFAULT_DELIMITER = "\t"

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
    }


def save_settings(settings: dict) -> None:
    """Persist *settings* dict to QSettings."""
    s = QSettings("PyPanTool", "PyPanTool")
    s.setValue("pattern", settings["pattern"])
    s.setValue("in_encoding", settings["in_encoding"])
    s.setValue("out_encoding", settings["out_encoding"])
    s.setValue("delimiter", settings["delimiter"])


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

        form = QFormLayout()
        form.addRow("Output name pattern:", self._pattern)
        form.addRow("Input encoding:", self._in_enc)
        form.addRow("Output encoding:", self._out_enc)
        form.addRow("Column delimiter:", self._delim)

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
        })
        self.accept()
