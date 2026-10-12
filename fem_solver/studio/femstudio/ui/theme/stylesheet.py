from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QWidget

from femstudio.ui.theme import tokens as t
from femstudio.ui.theme import zoom


def resolve_fonts(factor: float = 1.0) -> tuple[QFont, QFont]:
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
    sans.setPointSizeF(zoom.pt(t.BASE_PT, factor))
    mono.setPointSizeF(zoom.pt(t.BASE_PT, factor))
    return sans, mono


def build_stylesheet(sans: str, mono: str, factor: float = 1.0) -> str:
    """The Qt stylesheet for the whole window, from the tokens, the font families and the zoom."""

    def px(value: float) -> str:
        return f"{zoom.px(value, factor)}px"

    def pt(value: float) -> str:
        return f"{zoom.pt(value, factor):g}pt"

    rule = f"{t.RULE_WIDTH}px solid {t.RULE}"
    return f"""
* {{ font-family: "{sans}"; font-size: {pt(t.BASE_PT)}; color: {t.INK}; }}
QMainWindow, QDialog {{ background: {t.PANEL}; }}
QToolTip {{ background: {t.SURFACE}; color: {t.INK}; border: {rule}; }}

QMenuBar {{ background: {t.CHROME}; border-bottom: {rule}; }}
QMenuBar::item {{ padding: {px(4)} {px(10)}; background: transparent; }}
QMenuBar::item:selected {{ background: {t.SELECTION}; }}
QMenu {{ background: {t.SURFACE}; border: {rule}; }}
QMenu::item {{ padding: {px(4)} {px(22)}; }}
QMenu::item:selected {{ background: {t.SELECTION}; }}
QMenu::item:disabled {{ color: {t.MUTED}; }}

QToolBar#workflowToolBar {{ background: {t.SURFACE}; border: none;
  border-bottom: {rule}; spacing: 0; padding: 0; }}
QToolButton#step {{ background: transparent; border: none; border-bottom: 2px solid transparent;
  padding: {px(8)} {px(16)}; color: {t.MUTED}; }}
QToolButton#step:checked {{ color: {t.ACCENT}; border-bottom-color: {t.ACCENT}; font-weight: 600; }}
QToolButton#step:hover:!checked {{ color: {t.INK}; }}
QComboBox#backend {{ border: {rule}; border-radius: {px(t.RADIUS)};
  padding: {px(3)} {px(10)}; background: {t.SURFACE}; }}
QComboBox#backend QAbstractItemView {{ background: {t.SURFACE};
  border: {rule}; selection-background-color: {t.SELECTION};
  selection-color: {t.INK}; }}
QPushButton#run {{ background: {t.ACCENT}; color: {t.ON_ACCENT}; border: none;
  border-radius: {px(t.RADIUS)}; padding: {px(5)} {px(16)}; font-weight: 600; }}
QPushButton#run:disabled {{ background: {t.RULE}; color: {t.MUTED}; }}

QDockWidget {{ background: {t.SURFACE}; }}
QDockWidget > QWidget {{ background: {t.SURFACE}; }}
QWidget#dockTitle {{ background: {t.PANEL}; border-bottom: {rule}; }}
QLabel#dockTitleText {{ color: {t.MUTED}; font-size: {pt(t.TITLE_PT)}; font-weight: 600;
  letter-spacing: {px(1)}; background: transparent; }}
QToolButton#dockClose {{ border: none; background: transparent; color: {t.MUTED};
  padding: 0 {px(4)}; }}
QToolButton#dockClose:hover {{ color: {t.INK}; }}

QTreeWidget#sceneTree {{ background: {t.SURFACE}; border: none; outline: 0;
  padding-left: {px(t.GAP)}; }}
QTreeWidget#sceneTree::item {{ min-height: {px(t.ROW_HEIGHT)}; }}
QTreeWidget#sceneTree::item:selected {{ background: {t.SELECTION}; color: {t.INK}; }}

QTabWidget#viewport::pane {{ border: none; border-top: {rule}; background: {t.STAGE}; }}
QTabWidget#viewport > QWidget {{ background: {t.STAGE}; }}
QTabBar {{ background: {t.STAGE}; }}
QTabBar::tab {{ padding: {px(5)} {px(12)}; border: {rule}; border-bottom: none;
  border-top-left-radius: {px(t.RADIUS)}; border-top-right-radius: {px(t.RADIUS)};
  background: {t.PANEL}; color: {t.MUTED}; margin-right: {px(2)}; }}
QTabBar::tab:selected {{ background: {t.STAGE}; color: {t.INK}; font-weight: 600; }}
QLabel#placeholder {{ color: {t.MUTED}; background: {t.STAGE}; }}

QWidget#propertiesBody {{ background: {t.SURFACE}; }}
QLabel[role="heading"] {{ font-weight: 600; }}
QLabel[role="key"] {{ color: {t.MUTED}; }}
QLabel[role="value"] {{ font-family: "{mono}"; }}
QLabel[role="field"] {{ border: {rule}; border-radius: {px(3)};
  padding: {px(3)} {px(7)}; background: {t.SURFACE}; font-family: "{mono}"; }}
QLabel[role="note"] {{ color: {t.MUTED}; }}

QPlainTextEdit#log {{ background: {t.SURFACE}; border: none;
  border-top: {rule}; color: {t.MUTED}; font-family: "{mono}";
  font-size: {pt(t.SMALL_PT)}; padding: {px(4)} {px(8)}; }}

QStatusBar {{ background: {t.CHROME}; border-top: {rule};
  color: {t.MUTED}; }}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ color: {t.MUTED}; font-size: {pt(t.SMALL_PT)}; padding: 0 {px(8)}; }}
QPushButton#validation {{ border: none; background: transparent; font-size: {pt(t.SMALL_PT)};
  padding: 0 {px(8)}; }}
QPushButton#validation[level="ok"] {{ color: {t.SUCCESS}; }}
QPushButton#validation[level="warning"] {{ color: {t.WARNING}; }}
QPushButton#validation[level="error"] {{ color: {t.ERROR}; }}

QDialog QListWidget {{ background: {t.SURFACE}; border: {rule}; }}
QPushButton {{ border: {rule}; border-radius: {px(t.RADIUS)};
  padding: {px(4)} {px(12)}; background: {t.SURFACE}; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit {{ border: {rule};
  border-radius: {px(3)}; padding: {px(3)} {px(6)}; background: {t.SURFACE};
  font-family: "{mono}"; selection-background-color: {t.SELECTION}; selection-color: {t.INK}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
QPlainTextEdit:focus {{
  border: {t.RULE_WIDTH}px solid {t.ACCENT}; }}
QLineEdit[state="invalid"] {{ border: {t.RULE_WIDTH}px solid {t.ERROR}; }}
QToolButton#add_operand {{ border: {rule}; border-radius: {px(3)}; padding: {px(2)} {px(8)};
  background: {t.SURFACE}; }}
QSplitter::handle {{ background: {t.RULE}; }}
"""


def apply(window: QWidget, factor: float) -> None:
    """Set fonts and stylesheet for `factor`; widgets that size things in code refresh."""
    sans, mono = resolve_fonts(factor)
    window.setFont(sans)
    window.setStyleSheet(build_stylesheet(sans.family(), mono.family(), factor))
    for widget in window.findChildren(QWidget):
        hook = getattr(widget, "apply_zoom", None)
        if callable(hook):
            hook()
