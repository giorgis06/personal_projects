from PySide6.QtWidgets import QVBoxLayout, QWidget

from femstudio.core.mesh.quality import quality
from femstudio.core.project.document import Document
from femstudio.ui.widgets.readouts import PairsGrid, Section


class MeshPanel(QWidget):
    """What the mesh holds: counts, element quality and the triangles of each region."""

    def __init__(self) -> None:
        super().__init__()
        self._grid = PairsGrid()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(Section("Mesh", self._grid))
        layout.addStretch(1)

    def rows(self) -> list[tuple[str, str]]:
        return self._grid.rows

    def update_view(self, document: Document | None, kind: str, name: str) -> None:
        if document is None:
            self._grid.set_rows([("mesh", "none")])
            return
        stats = quality(document.mesh)
        rows = [
            ("nodes", f"{stats.n_nodes}"),
            ("triangles", f"{stats.n_triangles}"),
            ("min angle", f"{stats.min_angle:.1f} deg"),
            ("longest edge", f"{stats.max_edge:.3g}"),
            ("area", f"{stats.total_area:.4g}"),
        ]
        if document.size is not None:
            rows.insert(0, ("element size", f"{document.size:.3g}"))
        for region, ids in document.mesh.regions.items():
            rows.append((region, f"{len(ids)} triangles"))
        self._grid.set_rows(rows)
