from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QHBoxLayout, QLabel, QToolButton, QWidget

from femstudio.ui.theme import tokens as t
from femstudio.ui.theme import zoom


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
        self._layout = QHBoxLayout(self)
        layout = self._layout
        self.apply_zoom()
        layout.addWidget(label)
        layout.addStretch(1)
        layout.addWidget(close)

    def apply_zoom(self) -> None:
        pad, gap = zoom.px(t.PANEL_PAD), zoom.px(t.GAP)
        self._layout.setContentsMargins(pad, gap, zoom.px(t.PAD), gap)
