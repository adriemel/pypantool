"""Dialog for Split by Lines / Split by Columns / Split Large File."""

from functools import partial

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.columns import parse_column_spec
from core.split import split_by_columns, split_by_lines, split_by_size
from gui.run_tool import run_split


class SplitDialog(QDialog):
    """Collect split parameters and fan each loaded file into chunk files."""

    def __init__(self, main_window, mode: str, parent: QWidget | None = None) -> None:
        """
        Args:
            main_window: The :class:`~gui.main_window.MainWindow` instance.
            mode:        ``"lines"``, ``"columns"``, or ``"large"``.
        """
        super().__init__(parent or main_window)
        self._mw = main_window
        self._mode = mode

        titles = {
            "lines": "Split by Lines",
            "columns": "Split by Columns",
            "large": "Split Large File",
        }
        self.setWindowTitle(titles[mode])
        self.setMinimumWidth(380)

        form = QFormLayout()

        self._lines_per_file: QSpinBox | None = None
        self._max_mb: QSpinBox | None = None
        self._max_lines: QSpinBox | None = None
        self._header_lines: QSpinBox | None = None
        self._cols_per_file: QSpinBox | None = None
        self._fixed_spec: QLineEdit | None = None

        if mode == "lines":
            self._lines_per_file = QSpinBox()
            self._lines_per_file.setRange(1, 2_000_000_000)
            self._lines_per_file.setValue(100_000)
            form.addRow("Lines per file:", self._lines_per_file)
            self._add_header_row(form)
            hint = "Each output file gets this many data lines."
        elif mode == "large":
            self._max_mb = QSpinBox()
            self._max_mb.setRange(1, 100_000)
            self._max_mb.setValue(100)
            self._max_mb.setSuffix(" MB")
            form.addRow("Maximum file size:", self._max_mb)
            self._max_lines = QSpinBox()
            self._max_lines.setRange(1, 2_000_000_000)
            self._max_lines.setValue(1_000_000)
            form.addRow("Maximum lines per file:", self._max_lines)
            self._add_header_row(form)
            hint = "A new output file starts when either limit is reached."
        else:
            self._cols_per_file = QSpinBox()
            self._cols_per_file.setRange(1, 100_000)
            self._cols_per_file.setValue(1)
            form.addRow("Data columns per file:", self._cols_per_file)
            self._fixed_spec = QLineEdit()
            self._fixed_spec.setPlaceholderText("e.g. 1-2 (optional)")
            form.addRow("Fixed columns:", self._fixed_spec)
            hint = (
                "Fixed columns are repeated in every output file;\n"
                "the remaining columns are dealt out in order."
            )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            hint + "\nOutput files are numbered <tt>name_0001</tt>, "
            "<tt>name_0002</tt>, …"
        ))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _add_header_row(self, form: QFormLayout) -> None:
        self._header_lines = QSpinBox()
        self._header_lines.setRange(0, 10_000)
        self._header_lines.setValue(1)
        form.addRow("Header lines to repeat:", self._header_lines)

    def _accept(self) -> None:
        settings = self._mw.current_settings()
        delimiter = settings.get("delimiter", "\t")

        if self._mode == "lines":
            fn = partial(
                split_by_lines,
                lines_per_file=self._lines_per_file.value(),
                header_lines=self._header_lines.value(),
            )
            label = "Split by lines"
            sequential = True
        elif self._mode == "large":
            fn = partial(
                split_by_size,
                max_bytes=self._max_mb.value() * 1_000_000,
                max_lines=self._max_lines.value(),
                header_lines=self._header_lines.value(),
            )
            label = "Split large file"
            sequential = True
        else:
            spec = self._fixed_spec.text().strip()
            if spec:
                try:
                    parse_column_spec(spec, total=1_000_000)
                except ValueError as exc:
                    QMessageBox.warning(self, "Invalid fixed columns", str(exc))
                    return
            fn = partial(
                split_by_columns,
                columns_per_file=self._cols_per_file.value(),
                fixed_spec=spec,
                delimiter=delimiter,
            )
            label = "Split by columns"
            sequential = False

        self.accept()
        run_split(self._mw, fn, label, sequential=sequential)
