from PySide6.QtWidgets import QVBoxLayout, QWidget

from femstudio.backends import registry as backends
from femstudio.core.project.document import Document
from femstudio.physics.base import SolverSettings
from femstudio.ui.widgets.readouts import PairsGrid, Section


class SolvePanel(QWidget):
    """The backend and solver settings a run would use."""

    def __init__(self) -> None:
        super().__init__()
        self._grid = PairsGrid()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(Section("Solve", self._grid))
        layout.addStretch(1)
        self._backend = ""

    def rows(self) -> list[tuple[str, str]]:
        return self._grid.rows

    def set_backend(self, name: str) -> None:
        self._backend = name
        self._refresh(None)

    def update_view(self, document: Document | None, kind: str, name: str) -> None:
        self._refresh(document)

    def _refresh(self, document: Document | None) -> None:
        settings = SolverSettings()
        rows = []
        if self._backend:
            try:
                available = backends.get(self._backend).is_available()
            except KeyError:
                available = False
            rows.append(("backend", self._backend))
            rows.append(("available", "yes" if available else "no"))
        rows += [
            ("method", settings.method),
            ("tolerance", f"{settings.tolerance:g}"),
            ("max iterations", f"{settings.max_iterations}"),
        ]
        self._grid.set_rows(rows)
