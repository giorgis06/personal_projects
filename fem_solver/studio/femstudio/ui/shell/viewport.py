from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTabWidget

from femstudio.core.project.document import Document
from femstudio.ui.views.geometry_view import GeometryView
from femstudio.ui.views.mesh_view import MeshView

TABS = ("Heatmap", "3D surface", "Mesh", "Geometry")
TAB_FOR_STEP = {
    "Geometry": "Geometry",
    "Physics": "Geometry",
    "Mesh": "Mesh",
    "Solve": "Mesh",
    "Results": "Heatmap",
}
NO_RESULT = "No result yet. Run a solve to see the field here."


class Viewport(QTabWidget):
    """The centre: Heatmap, 3D surface, Mesh and Geometry tabs. The only region that stretches."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("viewport")
        self.setDocumentMode(False)
        self.geometry_view = GeometryView()
        self.mesh_view = MeshView()
        pages = {
            "Heatmap": self._placeholder(),
            "3D surface": self._placeholder(),
            "Mesh": self.mesh_view,
            "Geometry": self.geometry_view,
        }
        for title in TABS:
            self.addTab(pages[title], title)

    @staticmethod
    def _placeholder() -> QLabel:
        note = QLabel(NO_RESULT)
        note.setObjectName("placeholder")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return note

    def tab_titles(self) -> list[str]:
        return [self.tabText(i) for i in range(self.count())]

    def show_tab(self, title: str) -> None:
        self.setCurrentIndex(TABS.index(title))

    def current_title(self) -> str:
        return self.tabText(self.currentIndex())

    def set_document(self, document: Document | None) -> None:
        self.geometry_view.set_document(document)
        self.mesh_view.set_document(document)

    def highlight(self, kind: str, name: str) -> None:
        self.geometry_view.highlight(kind, name)
        self.mesh_view.highlight(kind, name)

    def close_views(self) -> None:
        self.geometry_view.close_plotter()
        self.mesh_view.close_plotter()
