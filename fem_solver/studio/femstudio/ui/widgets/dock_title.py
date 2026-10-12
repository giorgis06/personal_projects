from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QHBoxLayout, QLabel, QToolButton, QWidget

from femstudio.ui.theme import tokens as t


class DockTitle(QWidget):
    """A dock's title strip: the title in small capitals, and a button that closes the dock."""

    def __init__(self, text: str, dock: QDockWidget) -> None:
        super().__init__(dock)
        self.setObjectName("dockTitle")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        label = QLabel(text.upper())
        label.setObjectName("dockTitleText")
        close = QToolButton()
        close.setObjectName("dockClose")
        close.setText("×")
        close.setToolTip("Close")
        close.clicked.connect(dock.close)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(t.PANEL_PAD, t.GAP, t.PAD, t.GAP)
        layout.addWidget(label)
        layout.addStretch(1)
        layout.addWidget(close)
