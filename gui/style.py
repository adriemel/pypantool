"""Application-wide Qt stylesheet and colour/font constants.

Look: paper and ink.  Hairline rules, no filled bars, numbers in a
monospaced face.  Two signal colours only:

  TEAL   selection, header row of the peek pane, links
  AMBER  "have a look at this" (wrong encoding, ragged rows, failed values)
"""

from PySide6.QtGui import QFont

PAPER = "#FBFAF7"      # window and table background
PANEL = "#F2F0EA"      # status bar, rulers
INK = "#1D2126"        # text, primary button
MUTED = "#70747B"      # secondary text
RULE = "#DAD6CB"       # hairlines
RULE_SOFT = "#ECE9E1"  # row separators
TEAL = "#0E6B6B"
TEAL_BG = "#DCEAE7"
AMBER = "#A85A00"
AMBER_BG = "#FFF4E0"

UI_FAMILIES = ["Segoe UI", "Inter", "Arial"]
MONO_FAMILIES = ["Cascadia Mono", "Consolas", "JetBrains Mono", "DejaVu Sans Mono"]
_UI = ", ".join(f'"{f}"' for f in UI_FAMILIES) + ", sans-serif"
_MONO = ", ".join(f'"{f}"' for f in MONO_FAMILIES) + ", monospace"


def mono_font(point_size: float = 8.5, bold: bool = False) -> QFont:
    """Monospaced font for numbers and file content."""
    font = QFont(MONO_FAMILIES)
    font.setPointSizeF(point_size)
    font.setBold(bold)
    return font


STYLESHEET = f"""
/* ── Base ────────────────────────────────────────────────────── */
QWidget {{
    font-family: {_UI};
    font-size: 9pt;
    color: {INK};
}}
QMainWindow, QDialog, QWidget#central, QStackedWidget, QSplitter {{
    background-color: {PAPER};
}}
QLabel {{ background: transparent; }}
QLabel#caption {{
    color: {MUTED}; font-size: 7.5pt; font-weight: 600; letter-spacing: 1px;
}}
QLabel#muted {{ color: {MUTED}; }}
QLabel#monoMuted {{ color: {MUTED}; font-family: {_MONO}; font-size: 8pt; }}
QLabel#context {{ font-weight: 600; }}
QLabel#dropPlaceholder {{
    color: {MUTED};
    font-size: 13pt;
    border: 1px dashed #B9B4A7;
    margin: 28px;
    qproperty-alignment: AlignCenter;
}}

/* ── Menus ───────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {PAPER};
    border-bottom: 1px solid {RULE};
    padding: 1px 4px;
}}
QMenuBar::item {{ padding: 5px 10px; background: transparent; }}
QMenuBar::item:selected {{ background-color: {PANEL}; }}
QMenuBar::item:disabled {{ color: #A9ABB0; }}
QMenu {{
    background-color: #FFFFFF;
    border: 1px solid #B9B4A7;
    padding: 4px 0px;
}}
QMenu::item {{ padding: 5px 28px 5px 16px; background: transparent; }}
QMenu::item:selected {{ background-color: {TEAL_BG}; color: {INK}; }}
QMenu::item:disabled {{ color: #A9ABB0; }}
QMenu::separator {{ height: 1px; background: {RULE}; margin: 4px 10px; }}

/* ── Toolbar ─────────────────────────────────────────────────── */
QToolBar {{
    background-color: {PAPER};
    border: none;
    border-bottom: 1px solid {RULE};
    spacing: 2px;
    padding: 4px 8px;
}}
QToolBar::separator {{ width: 1px; background: {RULE}; margin: 5px 6px; }}
QToolBar QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    padding: 4px 10px;
}}
QToolBar QToolButton:hover {{ border-color: #B9B4A7; }}
QToolBar QToolButton:pressed {{ background-color: {PANEL}; }}
QToolBar QToolButton:disabled {{ color: #A9ABB0; }}
QToolBar QToolButton#settingsChip {{
    font-family: {_MONO};
    font-size: 8pt;
    color: {MUTED};
    border: 1px solid {RULE};
    padding: 3px 9px;
}}
QToolBar QToolButton#settingsChip:hover {{ color: {INK}; border-color: #B9B4A7; }}

/* ── Tables ──────────────────────────────────────────────────── */
QTableWidget {{
    background-color: {PAPER};
    alternate-background-color: #F6F4EE;
    border: none;
    border-top: 1px solid {RULE};
    gridline-color: {RULE_SOFT};
    selection-background-color: {TEAL_BG};
    selection-color: {INK};
    outline: none;
}}
QTableWidget::item {{ padding: 0px 8px; }}
QTableWidget::item:selected {{ background-color: {TEAL_BG}; color: {INK}; }}
QDialog QTableWidget {{ border: 1px solid {RULE}; }}
QHeaderView {{ background-color: {PAPER}; }}
QHeaderView::section {{
    background-color: {PAPER};
    color: {MUTED};
    font-size: 7.5pt;
    font-weight: 600;
    padding: 5px 8px;
    border: none;
    border-bottom: 1px solid {RULE};
}}
QTableWidget#peek QHeaderView::section {{
    background-color: {PANEL};
    font-family: {_MONO};
    font-size: 8pt;
    font-weight: normal;
    border-right: 1px solid {RULE};
}}
QTableCornerButton::section {{ background-color: {PANEL}; border: none; }}
QSplitter::handle {{ background-color: {RULE}; }}

/* ── Buttons ─────────────────────────────────────────────────── */
QPushButton {{
    background-color: {PAPER};
    border: 1px solid #B9B4A7;
    padding: 5px 16px;
    min-width: 64px;
}}
QPushButton:hover {{ border-color: {INK}; }}
QPushButton:pressed {{ background-color: {PANEL}; }}
QPushButton:disabled {{ color: #A9ABB0; border-color: {RULE}; }}
QPushButton:default {{
    background-color: {INK};
    color: {PAPER};
    border-color: {INK};
    font-weight: 600;
}}
QPushButton:default:hover {{ background-color: #343A42; }}
QPushButton:default:disabled {{
    background-color: #B9B4A7; border-color: #B9B4A7; color: {PAPER};
}}
QPushButton#link {{
    border: none; color: {TEAL}; padding: 2px 6px; min-width: 0px;
}}
QPushButton#link:hover {{ text-decoration: underline; }}
QPushButton#link:disabled {{ color: #A9ABB0; }}

/* ── Inputs (spin boxes, combo boxes and check boxes stay native) ─ */
QLineEdit, QPlainTextEdit, QTextEdit {{
    background-color: #FFFFFF;
    border: 1px solid {RULE};
    padding: 4px 8px;
    selection-background-color: {TEAL_BG};
    selection-color: {INK};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{ border-color: {TEAL}; }}
QLineEdit:read-only {{ background-color: {PANEL}; color: {MUTED}; }}
QListWidget {{
    background-color: #FFFFFF; border: 1px solid {RULE}; outline: none;
}}
QListWidget::item {{ padding: 4px 8px; }}
QListWidget::item:selected {{ background-color: {TEAL_BG}; color: {INK}; }}

/* ── Status bar ──────────────────────────────────────────────── */
QStatusBar {{
    background-color: {PANEL};
    border-top: 1px solid {RULE};
}}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ color: {MUTED}; padding: 2px 8px; }}
QStatusBar QPushButton {{ padding: 2px 12px; }}
QProgressBar {{
    max-height: 6px;
    min-width: 160px;
    border: none;
    background-color: {RULE};
}}
QProgressBar::chunk {{ background-color: {TEAL}; }}
"""
