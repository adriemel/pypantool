"""Dialog for Convert Date/Time to ISO 8601."""

from functools import partial

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from core.datetime_convert import convert_datetime
from gui.options_dialog import table_options
from gui.peek import header_and_first_row
from gui.run_tool import run_tool

_FORMATS = [
    "dd.MM.yyyy HH:mm:ss", "dd.MM.yyyy HH:mm", "dd.MM.yyyy", "d.M.yyyy H:mm",
    "MM/dd/yyyy HH:mm:ss", "M/d/yyyy h:mm:ss AP", "dd/MM/yyyy HH:mm",
    "yyyy-MM-dd HH:mm:ss", "yyyy/MM/dd HH:mm", "yyyyMMdd HHmmss",
    "dd-MMM-yyyy HH:mm:ss", "yyyy DDD HH:mm", "excel", "unix",
]
_HELP = (
    "Tokens: yyyy yy · MM M MMM (Jan) · dd d · DDD (day of year) · HH H · mm m · "
    "ss s · zzz (fraction) · AP (am/pm).\nOther characters are literal; put letters "
    "in single quotes. Special formats: excel (serial day), unix (seconds).\n"
    "With a separate time column, describe date and time separated by one space."
)
_SHOWN_FAILURES = 5


class DateTimeDialog(QDialog):
    """Choose column(s) and input format; preview the result on the first row."""

    def __init__(self, main_window, parent: QWidget | None = None) -> None:
        super().__init__(parent or main_window)
        self._mw = main_window
        self.setWindowTitle("Convert Date/Time to ISO 8601")
        self.setMinimumWidth(560)

        self._settings = main_window.current_settings()
        self._options = table_options(self._settings)
        first = main_window.files[0]
        self._sample = header_and_first_row(
            first, self._settings["in_encoding"], self._options
        )
        names = self._sample[0].split(self._options["delimiter"]) if self._sample else []

        self._date_col = QComboBox()
        self._time_col = QComboBox()
        self._time_col.addItem("(none, date and time are in one column)")
        for number, name in enumerate(names, start=1):
            self._date_col.addItem(f"{number}: {name}")
            self._time_col.addItem(f"{number}: {name}")
        for index, name in enumerate(names):
            if "date" in name.lower():
                self._date_col.setCurrentIndex(index)
                break

        self._format = QComboBox()
        self._format.setEditable(True)
        self._format.addItems(_FORMATS)

        self._offset = QDoubleSpinBox()
        self._offset.setRange(-14.0, 14.0)
        self._offset.setDecimals(2)
        self._offset.setSingleStep(0.5)
        self._offset.setSuffix(" h")
        self._offset.setToolTip(
            "Time zone of the values in the file, e.g. 2 for UTC+2 (CEST).\n"
            "It is subtracted, so the output is in UTC. 0 = leave times as they are."
        )

        self._keep = QCheckBox("Keep the original column(s) and insert Date/Time before them")

        self._preview = QLabel()
        self._preview.setWordWrap(True)
        help_label = QLabel(_HELP)
        help_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Date column:", self._date_col)
        form.addRow("Separate time column:", self._time_col)
        form.addRow("Format in the file:", self._format)
        form.addRow("UTC offset of the times in the file:", self._offset)
        form.addRow("", self._keep)
        form.addRow("First data row:", self._preview)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Convert")
        self._ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Rewrites the chosen column as yyyy-MM-ddTHH:mm:ss in all loaded files.\n"
            f"Columns are read from {first.name}."
        ))
        layout.addLayout(form)
        layout.addWidget(help_label)
        layout.addWidget(buttons)

        for combo in (self._date_col, self._time_col):
            combo.currentIndexChanged.connect(self._update_preview)
        self._format.currentTextChanged.connect(self._update_preview)
        self._offset.valueChanged.connect(self._update_preview)
        self._keep.toggled.connect(self._update_preview)
        self._update_preview()

    def _params(self) -> dict:
        return {
            "date_column": self._date_col.currentIndex() + 1,
            "time_column": self._time_col.currentIndex(),
            "in_format": self._format.currentText(),
            "utc_offset_hours": self._offset.value(),
            "keep_original": self._keep.isChecked(),
        }

    def _update_preview(self) -> None:
        if not self._sample:
            self._preview.setText("No header or data row found in the first file.")
            self._ok.setEnabled(False)
            return
        params = self._params()
        delimiter = self._options["delimiter"]
        row = self._sample[1].split(delimiter)
        d, t = params["date_column"] - 1, params["time_column"] - 1
        before = row[d] if d < len(row) else ""
        if 0 <= t < len(row):
            before = f"{before} {row[t]}"
        failed: list[str] = []
        try:
            out = list(convert_datetime(
                list(self._sample), on_fail=lambda _n, text: failed.append(text),
                **params, **{**self._options, "header_line": 1},
            ))
        except ValueError as exc:
            self._preview.setText(str(exc))
            self._preview.setStyleSheet("color: #A85A00;")
            self._ok.setEnabled(False)
            return
        if failed:
            self._preview.setText(f"{before!r} does not match this format")
            self._preview.setStyleSheet("color: #A85A00;")
        else:
            after = out[1].split(delimiter)[d]
            self._preview.setText(f"{before}   →   {after}")
            self._preview.setStyleSheet("")
        self._ok.setEnabled(True)

    def _accept(self) -> None:
        params = self._params()
        failures: list[tuple[int, str]] = []
        count = [0]

        def on_fail(lineno: int, text: str) -> None:
            count[0] += 1
            if len(failures) < _SHOWN_FAILURES:
                failures.append((lineno, text))

        def on_done() -> None:
            if not count[0]:
                return
            listing = "\n".join(f"line {n:,}: {text}" for n, text in failures)
            QMessageBox.warning(
                self._mw, "Convert Date/Time",
                f"{count[0]:,} value(s) did not match the format and were left "
                f"unchanged. First ones:\n\n{listing}\n\n"
                "File Statistics on the output lists them as 'not ISO 8601'.",
            )

        self.accept()
        run_tool(
            self._mw,
            partial(convert_datetime, on_fail=on_fail, **params, **self._options),
            "Convert date/time",
            on_done=on_done,
        )
