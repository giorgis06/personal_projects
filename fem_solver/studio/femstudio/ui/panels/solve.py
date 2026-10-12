from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from femstudio.backends import registry as backends
from femstudio.core.project.document import Document
from femstudio.physics.base import ProblemError, SolverSettings
from femstudio.ui.session import Session
from femstudio.ui.widgets.readouts import PairsGrid, Section, label

MAX_ITERATIONS_LIMIT = 10_000_000


class SolvePanel(QWidget):
    """The backend that will run, and the solver settings a run is made with."""

    def __init__(self, session: Session) -> None:
        super().__init__()
        self._session = session
        self._backend = ""
        self._grid = PairsGrid()
        self._tolerance = QLineEdit()
        self._tolerance.setObjectName("tolerance")
        self._iterations = QSpinBox()
        self._iterations.setObjectName("iterations")
        self._iterations.setRange(1, MAX_ITERATIONS_LIMIT)
        self._apply = QPushButton("Apply")
        self._apply.setObjectName("apply")
        self._apply.clicked.connect(self.apply)
        settings = QWidget()
        form = QVBoxLayout(settings)
        form.setContentsMargins(0, 0, 0, 0)
        form.addWidget(label("tolerance", "key"))
        form.addWidget(self._tolerance)
        form.addWidget(label("max iterations", "key"))
        form.addWidget(self._iterations)
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(self._apply)
        row_layout.addStretch(1)
        form.addWidget(row)
        self._message = label("", "note")
        self._message.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(Section("Solve", self._grid))
        layout.addWidget(Section("Solver settings", settings))
        layout.addWidget(self._message)
        layout.addStretch(1)
        session.settingsChanged.connect(self._show_settings)
        self._show_settings()

    def rows(self) -> list[tuple[str, str]]:
        return self._grid.rows

    def message(self) -> str:
        return self._message.text()

    def set_backend(self, name: str) -> None:
        self._backend = name
        self._refresh()

    def update_view(self, document: Document | None, kind: str, name: str) -> None:
        self._refresh()

    def _refresh(self) -> None:
        settings = self._session.settings
        rows = []
        if self._backend:
            try:
                available = backends.get(self._backend).is_available()
            except KeyError:
                available = False
            rows.append(("backend", self._backend))
            rows.append(("available", "yes" if available else "no"))
        rows.append(("method", settings.method))
        self._grid.set_rows(rows)

    def _show_settings(self) -> None:
        settings = self._session.settings
        self._tolerance.setText(f"{settings.tolerance:g}")
        self._iterations.setValue(settings.max_iterations)
        self._refresh()

    def apply(self) -> None:
        """Use the tolerance and iteration limit in the boxes for the next run."""
        current = self._session.settings
        try:
            tolerance = float(self._tolerance.text())
        except ValueError:
            self._message.setText(f"'{self._tolerance.text()}' is not a number")
            return
        try:
            settings = SolverSettings(current.method, tolerance, self._iterations.value())
        except ProblemError as error:
            self._message.setText(str(error))
            return
        self._message.setText("")
        self._session.set_settings(settings)
