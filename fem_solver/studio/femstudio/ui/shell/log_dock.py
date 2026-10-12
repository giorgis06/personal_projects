from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QPlainTextEdit

from femstudio.ui.widgets.dock_title import DockTitle


class LogDock(QDockWidget):
    """Solver and mesher output as it arrives; read-only, scrolled to the newest line."""

    def __init__(self) -> None:
        super().__init__("Log")
        self.setObjectName("logDock")
        self.setTitleBarWidget(DockTitle("Log", self))
        self._text = QPlainTextEdit()
        self._text.setObjectName("log")
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setWidget(self._text)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)

    def append_line(self, line: str) -> None:
        self._text.appendPlainText(line.rstrip("\n"))
        bar = self._text.verticalScrollBar()
        bar.setValue(bar.maximum())

    def lines(self) -> list[str]:
        return self._text.toPlainText().splitlines()

    def clear(self) -> None:
        self._text.clear()
