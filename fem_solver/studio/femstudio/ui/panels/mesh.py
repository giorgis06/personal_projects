from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

from femstudio.core.mesh.quality import quality
from femstudio.core.project.document import Document
from femstudio.ui.session import Session
from femstudio.ui.widgets.readouts import PairsGrid, Section, label


class MeshPanel(QWidget):
    """The element size, and what the mesh holds: counts, quality and each region's triangles."""

    def __init__(self, session: Session) -> None:
        super().__init__()
        self._session = session
        self._size = QLineEdit()
        self._size.setObjectName("size")
        self._size.returnPressed.connect(self.apply)
        self._apply = QPushButton("Apply")
        self._apply.setObjectName("apply")
        self._apply.clicked.connect(self.apply)
        self._auto = QPushButton("Default")
        self._auto.setObjectName("default")
        self._auto.clicked.connect(self.use_default)
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        for widget in (self._size, self._apply, self._auto):
            controls_layout.addWidget(widget)
        self._message = label("", "note")
        self._message.setWordWrap(True)
        self._grid = PairsGrid()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(Section("Element size", controls))
        layout.addWidget(self._message)
        layout.addWidget(Section("Mesh", self._grid))
        layout.addStretch(1)
        session.editRefused.connect(self._message.setText)

    def rows(self) -> list[tuple[str, str]]:
        return self._grid.rows

    def size_text(self) -> str:
        return self._size.text()

    def message(self) -> str:
        return self._message.text()

    def set_size_text(self, text: str) -> None:
        self._size.setText(text)

    def apply(self) -> None:
        """Re-mesh at the size typed in the box."""
        try:
            size = float(self._size.text())
        except ValueError:
            self._message.setText(f"'{self._size.text()}' is not a number")
            return
        self._message.setText("")
        self._session.set_mesh_size(size)

    def use_default(self) -> None:
        self._message.setText("")
        self._session.set_mesh_size(None)

    def update_view(self, document: Document | None, kind: str, name: str) -> None:
        editable = document is not None and document.scene is not None
        for widget in (self._size, self._apply, self._auto):
            widget.setEnabled(editable)
        if document is not None and document.size is not None:
            self._size.setText(f"{document.size:g}")
        if document is None:
            self._grid.set_rows([("mesh", "none")])
            return
        if document.mesh is None:
            reason = document.mesh_error or "no mesh"
            self._grid.set_rows([("mesh", "not built"), ("reason", reason)])
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
