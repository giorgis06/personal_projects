from PySide6.QtGui import QFont, QFontDatabase

from femstudio.ui.theme import tokens as t


def resolve_fonts() -> tuple[QFont, QFont]:
    """The interface and monospace fonts: the designed ones if installed, else the system's."""
    installed = set(QFontDatabase.families())
    if t.SANS_FAMILY in installed:
        sans = QFont(t.SANS_FAMILY)
    else:
        sans = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
    if t.MONO_FAMILY in installed:
        mono = QFont(t.MONO_FAMILY)
    else:
        mono = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    sans.setPointSize(t.BASE_PT)
    mono.setPointSize(t.BASE_PT)
    return sans, mono


def build_stylesheet(sans: str, mono: str) -> str:
    """The Qt stylesheet for the whole window, from the tokens and the two font families."""
    return f"""
* {{ font-family: "{sans}"; font-size: {t.BASE_PT}pt; color: {t.INK}; }}
QMainWindow, QDialog {{ background: {t.PANEL}; }}
QToolTip {{ background: {t.SURFACE}; color: {t.INK}; border: {t.RULE_WIDTH}px solid {t.RULE}; }}

QMenuBar {{ background: {t.CHROME}; border-bottom: {t.RULE_WIDTH}px solid {t.RULE}; }}
QMenuBar::item {{ padding: 4px 10px; background: transparent; }}
QMenuBar::item:selected {{ background: {t.SELECTION}; }}
QMenu {{ background: {t.SURFACE}; border: {t.RULE_WIDTH}px solid {t.RULE}; }}
QMenu::item {{ padding: 4px 22px; }}
QMenu::item:selected {{ background: {t.SELECTION}; }}
QMenu::item:disabled {{ color: {t.MUTED}; }}

QToolBar#workflowToolBar {{ background: {t.SURFACE}; border: none;
  border-bottom: {t.RULE_WIDTH}px solid {t.RULE}; spacing: 0; padding: 0; }}
QToolButton#step {{ background: transparent; border: none; border-bottom: 2px solid transparent;
  padding: 8px 16px; color: {t.MUTED}; }}
QToolButton#step:checked {{ color: {t.ACCENT}; border-bottom-color: {t.ACCENT}; font-weight: 600; }}
QToolButton#step:hover:!checked {{ color: {t.INK}; }}
QComboBox#backend {{ border: {t.RULE_WIDTH}px solid {t.RULE}; border-radius: {t.RADIUS}px;
  padding: 3px 10px; background: {t.SURFACE}; }}
QComboBox#backend QAbstractItemView {{ background: {t.SURFACE};
  border: {t.RULE_WIDTH}px solid {t.RULE}; selection-background-color: {t.SELECTION};
  selection-color: {t.INK}; }}
QPushButton#run {{ background: {t.ACCENT}; color: {t.ON_ACCENT}; border: none;
  border-radius: {t.RADIUS}px; padding: 5px 16px; font-weight: 600; }}
QPushButton#run:disabled {{ background: {t.RULE}; color: {t.MUTED}; }}

QDockWidget {{ background: {t.SURFACE}; }}
QDockWidget > QWidget {{ background: {t.SURFACE}; }}
QWidget#dockTitle {{ background: {t.PANEL}; border-bottom: {t.RULE_WIDTH}px solid {t.RULE}; }}
QLabel#dockTitleText {{ color: {t.MUTED}; font-size: {t.TITLE_PT}pt; font-weight: 600;
  letter-spacing: 1px; background: transparent; }}
QToolButton#dockClose {{ border: none; background: transparent; color: {t.MUTED}; padding: 0 4px; }}
QToolButton#dockClose:hover {{ color: {t.INK}; }}

QTreeWidget#sceneTree {{ background: {t.SURFACE}; border: none; outline: 0; }}
QTreeWidget#sceneTree::item {{ min-height: {t.ROW_HEIGHT}px; }}
QTreeWidget#sceneTree::item:selected {{ background: {t.SELECTION}; color: {t.INK}; }}

QTabWidget#viewport::pane {{ border: none; border-top: {t.RULE_WIDTH}px solid {t.RULE};
  background: {t.STAGE}; }}
QTabWidget#viewport > QWidget {{ background: {t.STAGE}; }}
QTabBar {{ background: {t.STAGE}; }}
QTabBar::tab {{ padding: 5px 12px; border: {t.RULE_WIDTH}px solid {t.RULE}; border-bottom: none;
  border-top-left-radius: {t.RADIUS}px; border-top-right-radius: {t.RADIUS}px;
  background: {t.PANEL}; color: {t.MUTED}; margin-right: 2px; }}
QTabBar::tab:selected {{ background: {t.STAGE}; color: {t.INK}; font-weight: 600; }}
QLabel#placeholder {{ color: {t.MUTED}; background: {t.STAGE}; }}

QWidget#propertiesBody {{ background: {t.SURFACE}; }}
QLabel[role="heading"] {{ font-weight: 600; }}
QLabel[role="key"] {{ color: {t.MUTED}; }}
QLabel[role="value"] {{ font-family: "{mono}"; }}
QLabel[role="field"] {{ border: {t.RULE_WIDTH}px solid {t.RULE}; border-radius: 3px;
  padding: 3px 7px; background: {t.SURFACE}; font-family: "{mono}"; }}
QLabel[role="note"] {{ color: {t.MUTED}; }}

QPlainTextEdit#log {{ background: {t.SURFACE}; border: none;
  border-top: {t.RULE_WIDTH}px solid {t.RULE}; color: {t.MUTED}; font-family: "{mono}";
  font-size: {t.SMALL_PT}pt; padding: 4px 8px; }}

QStatusBar {{ background: {t.CHROME}; border-top: {t.RULE_WIDTH}px solid {t.RULE};
  color: {t.MUTED}; }}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ color: {t.MUTED}; font-size: {t.SMALL_PT}pt; padding: 0 8px; }}
QPushButton#validation {{ border: none; background: transparent; font-size: {t.SMALL_PT}pt;
  padding: 0 8px; }}
QPushButton#validation[level="ok"] {{ color: {t.SUCCESS}; }}
QPushButton#validation[level="warning"] {{ color: {t.WARNING}; }}
QPushButton#validation[level="error"] {{ color: {t.ERROR}; }}

QDialog QListWidget {{ background: {t.SURFACE}; border: {t.RULE_WIDTH}px solid {t.RULE}; }}
QPushButton {{ border: {t.RULE_WIDTH}px solid {t.RULE}; border-radius: {t.RADIUS}px;
  padding: 4px 12px; background: {t.SURFACE}; }}
QSplitter::handle {{ background: {t.RULE}; }}
"""
