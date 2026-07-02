"""Dialog for Extract 10 min Lines (time-series thinning)."""

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

from core.timeseries import extract_interval_lines
from gui.run_tool import run_tool


class TimeseriesDialog(QDialog):
    """Collect the thinning interval and run the extraction."""

    def __init__(self, main_window, parent: QWidget | None = None) -> None:
        super().__init__(parent or main_window)
        self._mw = main_window

        self.setWindowTitle("Extract 10 min Lines")
        self.setMinimumWidth(360)

        self._interval = QSpinBox()
        self._interval.setRange(1, 86_400_000)
        self._interval.setValue(600)
        self._interval.setSuffix(" s")

        self._keep_header = QCheckBox("Keep header line")
        self._keep_header.setChecked(True)

        form = QFormLayout()
        form.addRow("Minimum interval:", self._interval)
        form.addRow("", self._keep_header)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Keeps one line per interval based on the <b>Date/Time</b> column.\n"
            "Timestamps must be ISO format, e.g. <tt>2024-01-15T08:30:00</tt>."
        ))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        settings = self._mw.current_settings()
        delimiter = settings.get("delimiter", "\t")

        self.accept()
        run_tool(
            self._mw,
            partial(
                extract_interval_lines,
                interval_seconds=self._interval.value(),
                keep_header=self._keep_header.isChecked(),
                delimiter=delimiter,
            ),
            "Extract 10 min lines",
        )
