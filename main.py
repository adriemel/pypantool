"""PyPanTool — entry point."""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.style import STYLESHEET


def main() -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("PyPanTool")
    app.setOrganizationName("PyPanTool")
    app.setFont(QFont("Segoe UI", 9))
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(QIcon(str(Path(__file__).parent / "assets" / "pypantool.ico")))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
