"""Application-wide Qt stylesheet.

Palette — casual slate-blue:
  APP_BG       #ECF1F7   main window background
  SURFACE      #FFFFFF   tables, inputs
  HEADER_BG    #2B5C8F   menu bar + toolbar
  ACCENT       #3A7EC2   buttons, selection, header cells
  ACCENT_DARK  #2C6AAB   hover
  ACCENT_PALE  #E8F1FB   alternate table rows, light highlights
  SELECTION    #B5CEEC   selected row
  BORDER       #BDCFE0   input/table borders
  TEXT_MAIN    #1A2B3C   primary text
  TEXT_MUTED   #607585   secondary / disabled text
  STATUS_BG    #D6E4F0   status bar background
"""

STYLESHEET = """
/* ── Base ────────────────────────────────────────────────────── */
QWidget {
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 9pt;
    color: #1A2B3C;
    background-color: #ECF1F7;
}
QMainWindow, QDialog {
    background-color: #ECF1F7;
}

/* ── Menu bar ─────────────────────────────────────────────────── */
QMenuBar {
    background-color: #2B5C8F;
    color: #FFFFFF;
    padding: 2px 0px;
    spacing: 0px;
}
QMenuBar::item {
    padding: 5px 14px;
    background: transparent;
    border-radius: 0px;
}
QMenuBar::item:selected {
    background-color: #1C4266;
}
QMenuBar::item:pressed {
    background-color: #163252;
}

/* ── Menus ────────────────────────────────────────────────────── */
QMenu {
    background-color: #FFFFFF;
    border: 1px solid #BDCFE0;
    padding: 4px 0px;
}
QMenu::item {
    padding: 5px 24px 5px 14px;
    color: #1A2B3C;
    background: transparent;
}
QMenu::item:selected {
    background-color: #E8F1FB;
    color: #1A2B3C;
}
QMenu::item:disabled {
    color: #9AABB8;
}
QMenu::separator {
    height: 1px;
    background: #D0DDE8;
    margin: 3px 8px;
}

/* ── Toolbar ──────────────────────────────────────────────────── */
QToolBar {
    background-color: #2B5C8F;
    border: none;
    border-bottom: 1px solid #1C4266;
    spacing: 2px;
    padding: 3px 8px;
}
QToolBar::separator {
    width: 1px;
    background: #4A7DAF;
    margin: 4px 4px;
}
QToolBar QToolButton {
    color: #FFFFFF;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 9pt;
}
QToolBar QToolButton:hover {
    background-color: rgba(255, 255, 255, 0.15);
    border-color: rgba(255, 255, 255, 0.3);
}
QToolBar QToolButton:pressed {
    background-color: rgba(0, 0, 0, 0.2);
}
QToolBar QToolButton:disabled {
    color: #80A8C8;
}

/* ── File-list table ──────────────────────────────────────────── */
QTableWidget {
    background-color: #FFFFFF;
    alternate-background-color: #E8F1FB;
    gridline-color: #D0DDE8;
    border: 1px solid #BDCFE0;
    border-radius: 3px;
    selection-background-color: #B5CEEC;
    selection-color: #1A2B3C;
    outline: none;
}
QTableWidget::item {
    padding: 1px 8px;
    border: none;
}
QTableWidget::item:selected {
    background-color: #B5CEEC;
    color: #1A2B3C;
}

QHeaderView {
    background-color: #3A7EC2;
}
QHeaderView::section {
    background-color: #3A7EC2;
    color: #FFFFFF;
    font-weight: bold;
    padding: 5px 8px;
    border: none;
    border-right: 1px solid #5593D2;
}
QHeaderView::section:last {
    border-right: none;
}
QHeaderView::section:hover {
    background-color: #2C6AAB;
}

/* ── Buttons ──────────────────────────────────────────────────── */
QPushButton {
    background-color: #3A7EC2;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 5px 18px;
    min-width: 72px;
}
QPushButton:hover {
    background-color: #2C6AAB;
}
QPushButton:pressed {
    background-color: #1F5390;
}
QPushButton:disabled {
    background-color: #AABFD4;
    color: #FFFFFF;
}

/* ── Text / line inputs ───────────────────────────────────────── */
QLineEdit, QSpinBox, QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #BDCFE0;
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: #B5CEEC;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #3A7EC2;
}
QLineEdit:read-only {
    background-color: #F0F5FA;
    color: #607585;
}
QSpinBox::up-button {
    width: 18px;
    border: none;
    border-left: 1px solid #BDCFE0;
    background: #EBF1F8;
    border-top-right-radius: 4px;
}
QSpinBox::down-button {
    width: 18px;
    border: none;
    border-left: 1px solid #BDCFE0;
    background: #EBF1F8;
    border-bottom-right-radius: 4px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: #D0DDE8;
}

/* ── Checkboxes ───────────────────────────────────────────────── */
QCheckBox {
    spacing: 6px;
    color: #1A2B3C;
    background: transparent;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #BDCFE0;
    border-radius: 3px;
    background: #FFFFFF;
}
QCheckBox::indicator:checked {
    background-color: #3A7EC2;
    border-color: #3A7EC2;
}
QCheckBox::indicator:hover {
    border-color: #3A7EC2;
}
QCheckBox::indicator:disabled {
    background: #EDF2F7;
    border-color: #C8D5E0;
}

/* ── Labels ───────────────────────────────────────────────────── */
QLabel {
    background: transparent;
    color: #1A2B3C;
}

/* Drop-zone placeholder ── shown when no files are loaded */
QLabel#dropPlaceholder {
    color: #8AAABF;
    font-size: 14pt;
    border: 2px dashed #C0D3E5;
    border-radius: 8px;
    qproperty-alignment: AlignCenter;
}

/* ── Status bar ───────────────────────────────────────────────── */
QStatusBar {
    background-color: #D6E4F0;
    border-top: 1px solid #BDCFE0;
    color: #2B4A68;
    font-size: 9pt;
    padding: 0px 6px;
}
QStatusBar QLabel {
    color: #2B4A68;
    background: transparent;
    padding: 2px 0px;
}

/* ── Progress bar ─────────────────────────────────────────────── */
QProgressBar {
    max-height: 8px;
    min-width: 160px;
    border-radius: 4px;
    background-color: #BAD0E6;
    border: none;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #3A7EC2;
    border-radius: 4px;
}

/* ── Scrollbars ───────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #E4ECF4;
    width: 10px;
    border-radius: 5px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #AABFD4;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #8AAAC0;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #E4ECF4;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #AABFD4;
    border-radius: 5px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background: #8AAAC0;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ── Dialogs ──────────────────────────────────────────────────── */
QDialog QLabel {
    color: #374F65;
    font-size: 9pt;
}
QFormLayout QLabel {
    color: #374F65;
}
"""
