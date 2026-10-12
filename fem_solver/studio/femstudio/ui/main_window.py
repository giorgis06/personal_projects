import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QShowEvent
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox, QToolBar

from femstudio.backends import registry as backends
from femstudio.core.project.document import Document, open_document
from femstudio.physics import registry as physics
from femstudio.ui.shell.log_dock import LogDock
from femstudio.ui.shell.menu_bar import MainMenuBar
from femstudio.ui.shell.properties_dock import PropertiesDock
from femstudio.ui.shell.scene_dock import SceneDock
from femstudio.ui.shell.status_bar import StatusPanel
from femstudio.ui.shell.viewport import TAB_FOR_STEP, Viewport
from femstudio.ui.shell.workflow_bar import WorkflowBar
from femstudio.ui.theme import tokens as t
from femstudio.ui.theme.stylesheet import build_stylesheet, resolve_fonts

TITLE = "FEM Studio"
SOLVING_LATER = "Solving from the window arrives with the solve panel."


class MainWindow(QMainWindow):
    """Assembles the regions and connects their signals."""

    def __init__(self) -> None:
        super().__init__()
        sans, mono = resolve_fonts()
        self.setFont(sans)
        self.setStyleSheet(build_stylesheet(sans.family(), mono.family()))
        self.setWindowTitle(TITLE)
        self.resize(t.WINDOW_WIDTH, t.WINDOW_HEIGHT)
        self._workdir = tempfile.TemporaryDirectory(prefix="femstudio-")
        self._document: Document | None = None
        self._laid_out = False

        self.menu = MainMenuBar()
        self.setMenuBar(self.menu)
        self.workflow = WorkflowBar()
        toolbar = QToolBar("Workflow")
        toolbar.setObjectName("workflowToolBar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        toolbar.addWidget(self.workflow)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        self.viewport = Viewport()
        self.setCentralWidget(self.viewport)
        self.scene_dock = SceneDock()
        self.properties = PropertiesDock()
        self.log = LogDock()
        self.status = StatusPanel()
        self.setStatusBar(self.status)
        self.menu.set_docks([self.scene_dock, self.properties, self.log])

        self.workflow.set_backends([b.name for b in backends.available()])
        self.workflow.set_run_enabled(False, SOLVING_LATER)
        self.menu.set_run_enabled(False)
        self.properties.set_backend(self.workflow.backend())
        self._connect()
        self.reset_layout()
        self._on_step(self.workflow.step())

    def _connect(self) -> None:
        self.workflow.stepChanged.connect(self._on_step)
        self.workflow.backendChanged.connect(self.properties.set_backend)
        self.scene_dock.selectionChanged.connect(self._on_selection)
        self.menu.openFileRequested.connect(self._choose_file)
        self.menu.openFolderRequested.connect(self._choose_folder)
        self.menu.quitRequested.connect(self.close)
        self.menu.resetLayoutRequested.connect(self.reset_layout)

    def _on_step(self, step: str) -> None:
        self.properties.show_step(step)
        self.viewport.show_tab(TAB_FOR_STEP[step])

    def _on_selection(self, kind: str, name: str) -> None:
        self.properties.set_selection(kind, name)
        self.viewport.highlight(kind, name)

    def reset_layout(self) -> None:
        """The default arrangement: Scene left, Properties right, Log below."""
        areas = (
            (self.scene_dock, Qt.DockWidgetArea.LeftDockWidgetArea),
            (self.properties, Qt.DockWidgetArea.RightDockWidgetArea),
            (self.log, Qt.DockWidgetArea.BottomDockWidgetArea),
        )
        for dock, area in areas:
            dock.setFloating(False)
            self.addDockWidget(area, dock)
            dock.show()
        self.resizeDocks(
            [self.scene_dock, self.properties],
            [t.SCENE_DOCK_WIDTH, t.PROPERTIES_DOCK_WIDTH],
            Qt.Orientation.Horizontal,
        )
        self.resizeDocks([self.log], [t.LOG_DOCK_HEIGHT], Qt.Orientation.Vertical)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not self._laid_out:
            self._laid_out = True
            self.reset_layout()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.viewport.close_views()
        self._workdir.cleanup()
        super().closeEvent(event)

    @property
    def document(self) -> Document | None:
        return self._document

    def open_path(self, path: Path) -> bool:
        """Open a project folder, `scene.json`, `.msh` or `.geo`; show the reason on failure."""
        path = Path(path)
        self.log.append_line(f"[open] {path}")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            document = open_document(path, Path(self._workdir.name), self.log.append_line)
        except (ValueError, OSError) as error:
            self.log.append_line(f"[error] {error}")
            self.report_error(f"Cannot open {path.name}", str(error))
            return False
        finally:
            QApplication.restoreOverrideCursor()
        self._show(document)
        return True

    def report_error(self, title: str, message: str) -> None:
        QMessageBox.critical(self, title, message)

    def _show(self, document: Document) -> None:
        self._document = document
        problem_type = None
        if document.scene is not None:
            try:
                problem_type = physics.get(document.scene.problem_type)
            except KeyError as error:
                self.log.append_line(f"[warning] {error.args[0]}")
        self.setWindowTitle(f"{TITLE} - {document.source.name}")
        self.scene_dock.set_document(document, problem_type)
        self.properties.set_document(document)
        self.viewport.set_document(document)
        self.status.set_document(document)
        if document.mesh is None:
            self.log.append_line(f"[mesh] not built: {document.mesh_error}")
        else:
            mesh = document.mesh
            self.log.append_line(f"[open] {mesh.n_nodes} nodes, {mesh.n_triangles} triangles")

    def _choose_file(self) -> None:
        text = "Scene or mesh (*.json *.msh *.geo)"
        path, _ = QFileDialog.getOpenFileName(self, "Open", "", text)
        if path:
            self.open_path(Path(path))

    def _choose_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Open project folder")
        if path:
            self.open_path(Path(path))


def run(argv: list[str] | None = None) -> int:
    """Open the window, and a file if one is given, then block until it is closed."""
    arguments = sys.argv if argv is None else argv
    app = QApplication(arguments)
    window = MainWindow()
    window.show()
    if len(arguments) > 1:
        window.open_path(Path(arguments[1]))
    return app.exec()
