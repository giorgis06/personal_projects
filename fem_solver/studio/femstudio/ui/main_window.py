import sys
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QCloseEvent, QShowEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QToolBar,
    QWidget,
)

from femstudio.backends import registry as backends
from femstudio.core.project.document import Document
from femstudio.physics import registry as physics
from femstudio.ui.session import UNTITLED, Session
from femstudio.ui.shell.log_dock import LogDock
from femstudio.ui.shell.menu_bar import MainMenuBar
from femstudio.ui.shell.properties_dock import PropertiesDock
from femstudio.ui.shell.scene_dock import SceneDock
from femstudio.ui.shell.status_bar import StatusPanel
from femstudio.ui.shell.viewport import TAB_FOR_STEP, Viewport
from femstudio.ui.shell.workflow_bar import WorkflowBar
from femstudio.ui.theme import tokens as t
from femstudio.ui.theme import zoom
from femstudio.ui.theme.stylesheet import build_stylesheet, resolve_fonts

TITLE = "FEM Studio"
SOLVING_LATER = "Solving from the window arrives with the solve panel."


class MainWindow(QMainWindow):
    """Assembles the regions and connects their signals."""

    def __init__(self, settings: QSettings | None = None) -> None:
        super().__init__()
        self._settings = settings or QSettings("femstudio", "FEM Studio")
        zoom.set_current(zoom.load(self._settings))
        self.setWindowTitle(TITLE)
        self.resize(zoom.px(t.WINDOW_WIDTH), zoom.px(t.WINDOW_HEIGHT))
        self._laid_out = False
        self.session = Session()

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
        self.properties = PropertiesDock(self.session)
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
        self._apply_zoom()
        self._on_step(self.workflow.step())

    def _connect(self) -> None:
        self.workflow.stepChanged.connect(self._on_step)
        self.workflow.backendChanged.connect(self.properties.set_backend)
        self.scene_dock.selectionChanged.connect(self._on_selection)

        menu = self.menu
        menu.newSceneRequested.connect(self.new_scene)
        menu.openFileRequested.connect(self._choose_file)
        menu.openFolderRequested.connect(self._choose_folder)
        menu.saveRequested.connect(self.save)
        menu.saveAsRequested.connect(self._choose_save_path)
        menu.undoRequested.connect(self.session.undo)
        menu.redoRequested.connect(self.session.redo)
        menu.quitRequested.connect(self.close)
        menu.resetLayoutRequested.connect(self.reset_layout)
        menu.zoomInRequested.connect(lambda: self.set_zoom(zoom.zoomed_in(zoom.current())))
        menu.zoomOutRequested.connect(lambda: self.set_zoom(zoom.zoomed_out(zoom.current())))
        menu.zoomResetRequested.connect(lambda: self.set_zoom(1.0))

        session = self.session
        session.documentChanged.connect(self._on_document)
        session.historyChanged.connect(self._on_history)
        session.dirtyChanged.connect(lambda _dirty: self._update_title())
        session.selectionRequested.connect(self._select)
        session.logLine.connect(self.log.append_line)
        session.errorRaised.connect(self.report_error)

    def _on_step(self, step: str) -> None:
        self.properties.show_step(step)
        self.viewport.show_tab(TAB_FOR_STEP[step])

    def _on_selection(self, kind: str, name: str) -> None:
        self.properties.set_selection(kind, name)
        self.viewport.highlight(kind, name)

    def _select(self, kind: str, name: str) -> None:
        try:
            self.scene_dock.select(kind, name)
        except KeyError:
            pass

    def set_zoom(self, factor: float) -> None:
        """Scale the whole interface and remember the choice; the viewport drawing is not scaled."""
        zoom.set_current(factor)
        zoom.save(self._settings, zoom.current())
        self._apply_zoom()

    def _apply_zoom(self) -> None:
        factor = zoom.current()
        sans, mono = resolve_fonts(factor)
        self.setFont(sans)
        self.setStyleSheet(build_stylesheet(sans.family(), mono.family(), factor))
        for widget in self.findChildren(QWidget):
            hook = getattr(widget, "apply_zoom", None)
            if callable(hook):
                hook()
        self._size_docks()
        self.status.set_zoom(factor)
        self.menu.set_zoom_limits(factor < zoom.MAXIMUM, factor > zoom.MINIMUM)

    def _size_docks(self) -> None:
        self.resizeDocks(
            [self.scene_dock, self.properties],
            [zoom.px(t.SCENE_DOCK_WIDTH), zoom.px(t.PROPERTIES_DOCK_WIDTH)],
            Qt.Orientation.Horizontal,
        )
        self.resizeDocks([self.log], [zoom.px(t.LOG_DOCK_HEIGHT)], Qt.Orientation.Vertical)

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
        self._size_docks()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not self._laid_out:
            self._laid_out = True
            self.reset_layout()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.viewport.close_views()
        self.session.close()
        super().closeEvent(event)

    @property
    def document(self) -> Document | None:
        return self.session.document

    # -- files and the scene being edited

    def open_path(self, path: Path) -> bool:
        """Open a project folder, `scene.json`, `.msh` or `.geo`; the reason is shown on failure."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            return self.session.open_path(Path(path))
        finally:
            QApplication.restoreOverrideCursor()

    def new_scene(self) -> bool:
        types = [p.name for p in physics.available()]
        if not types:
            self.report_error("New scene", "no problem type is available")
            return False
        problem = types[0]
        if len(types) > 1:
            problem, chosen = QInputDialog.getItem(
                self, "New scene", "Problem type", types, 0, False
            )
            if not chosen:
                return False
        self.session.new_scene(problem)
        return True

    def save(self, path: Path | None = None) -> bool:
        """Save into the project, to `path`, or ask for a name when the scene has none yet."""
        document = self.session.document
        if path is None and document is not None and document.project is None:
            if document.source == UNTITLED or document.source.suffix != ".json":
                return self._choose_save_path()
        return self.session.save(path)

    def _choose_save_path(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(self, "Save scene", "", "Scene (*.json)")
        if not path:
            return False
        return self.session.save(Path(path))

    def report_error(self, title: str, message: str) -> None:
        QMessageBox.critical(self, title, message)

    def _on_document(self, document: Document | None, reset_view: bool) -> None:
        problem_type = None
        if document is not None and document.scene is not None:
            try:
                problem_type = physics.get(document.scene.problem_type)
            except KeyError as error:
                self.log.append_line(f"[warning] {error.args[0]}")
        keep = not reset_view
        self.scene_dock.set_document(document, problem_type, keep_selection=keep)
        self.properties.set_document(document, keep_selection=keep)
        self.viewport.set_document(document, reset_view)
        self.status.set_document(document)
        self.menu.set_saveable(document is not None and document.scene is not None)
        self._update_title()
        if document is not None and reset_view:
            if document.mesh is None:
                self.log.append_line(f"[mesh] not built: {document.mesh_error}")
            else:
                mesh = document.mesh
                self.log.append_line(f"[open] {mesh.n_nodes} nodes, {mesh.n_triangles} triangles")

    def _on_history(self) -> None:
        history = self.session.history
        self.menu.set_history(history.undo_label, history.redo_label)

    def _update_title(self) -> None:
        document = self.session.document
        if document is None:
            self.setWindowTitle(TITLE)
            return
        mark = "*" if self.session.dirty else ""
        self.setWindowTitle(f"{TITLE} - {document.source.name}{mark}")

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
