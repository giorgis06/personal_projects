from PySide6.QtWidgets import QTabWidget

from femstudio.core.project.document import Document
from femstudio.ui.results_state import ResultsState
from femstudio.ui.views.geometry_view import GeometryView
from femstudio.ui.views.heatmap_view import HeatmapView
from femstudio.ui.views.mesh_view import MeshView
from femstudio.ui.views.surface_view import SurfaceView

TABS = ("Heatmap", "3D surface", "Mesh", "Geometry")
TAB_FOR_STEP = {
    "Geometry": "Geometry",
    "Physics": "Geometry",
    "Mesh": "Mesh",
    "Solve": "Mesh",
    "Results": "Heatmap",
}


class Viewport(QTabWidget):
    """The centre: Heatmap, 3D surface, Mesh and Geometry tabs. The only region that stretches."""

    def __init__(self, results: ResultsState) -> None:
        super().__init__()
        self.setObjectName("viewport")
        self.setDocumentMode(False)
        self.heatmap_view = HeatmapView(results)
        self.surface_view = SurfaceView(results)
        self.geometry_view = GeometryView()
        self.mesh_view = MeshView()
        pages = {
            "Heatmap": self.heatmap_view,
            "3D surface": self.surface_view,
            "Mesh": self.mesh_view,
            "Geometry": self.geometry_view,
        }
        for title in TABS:
            self.addTab(pages[title], title)

    def tab_titles(self) -> list[str]:
        return [self.tabText(i) for i in range(self.count())]

    def show_tab(self, title: str) -> None:
        self.setCurrentIndex(TABS.index(title))

    def current_title(self) -> str:
        return self.tabText(self.currentIndex())

    def set_document(self, document: Document | None, reset_view: bool = True) -> None:
        self.geometry_view.set_document(document, reset_view)
        self.mesh_view.set_document(document, reset_view)

    def highlight(self, kind: str, name: str) -> None:
        self.geometry_view.highlight(kind, name)
        self.mesh_view.highlight(kind, name)

    def close_views(self) -> None:
        for view in (self.heatmap_view, self.surface_view, self.geometry_view, self.mesh_view):
            view.close_plotter()
