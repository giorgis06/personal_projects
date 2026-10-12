from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from femstudio.core.project.document import Document
from femstudio.ui.panels.geometry import GeometryPanel
from femstudio.ui.panels.mesh import MeshPanel
from femstudio.ui.panels.physics import PhysicsPanel
from femstudio.ui.panels.results import ResultsPanel
from femstudio.ui.panels.solve import SolvePanel
from femstudio.ui.session import Session
from femstudio.ui.theme import tokens as t
from femstudio.ui.theme import zoom
from femstudio.ui.widgets.dock_title import DockTitle


class PropertiesDock(QDockWidget):
    """Hosts the panel of the current step, showing what is selected in the scene."""

    def __init__(self, session: Session) -> None:
        super().__init__("Properties")
        self.setObjectName("propertiesDock")
        self.setTitleBarWidget(DockTitle("Properties", self))
        self._panels = {
            "Geometry": GeometryPanel(session),
            "Physics": PhysicsPanel(),
            "Mesh": MeshPanel(),
            "Solve": SolvePanel(),
            "Results": ResultsPanel(),
        }
        self._stack = QStackedWidget()
        for panel in self._panels.values():
            self._stack.addWidget(panel)
        body = QWidget()
        body.setObjectName("propertiesBody")
        self._body_layout = QVBoxLayout(body)
        self._body_layout.addWidget(self._stack)
        self.apply_zoom()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(body)
        self.setWidget(scroll)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self._document: Document | None = None
        self._selection = ("", "")

    def apply_zoom(self) -> None:
        pad = zoom.px(t.PANEL_PAD)
        self._body_layout.setContentsMargins(pad, pad, pad, pad)

    def panel(self, step: str) -> QWidget:
        return self._panels[step]

    def current_step(self) -> str:
        current = self._stack.currentWidget()
        return next(step for step, panel in self._panels.items() if panel is current)

    def show_step(self, step: str) -> None:
        self._stack.setCurrentWidget(self._panels[step])

    def set_document(self, document: Document | None, keep_selection: bool = False) -> None:
        self._document = document
        if not keep_selection:
            self._selection = ("", "")
        self._refresh()

    def set_selection(self, kind: str, name: str) -> None:
        self._selection = (kind, name)
        self._refresh()

    def set_backend(self, name: str) -> None:
        self._panels["Solve"].set_backend(name)

    def _refresh(self) -> None:
        kind, name = self._selection
        for panel in self._panels.values():
            panel.update_view(self._document, kind, name)
