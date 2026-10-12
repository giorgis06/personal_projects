import sys
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QCloseEvent, QShowEvent
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QToolBar,
)

from femstudio.backends import registry as backends
from femstudio.core.project.document import Document
from femstudio.physics import registry as physics
from femstudio.ui.runner import Runner, why_not_runnable
from femstudio.ui.session import RunRefused, Session
from femstudio.ui.shell.file_actions import FileActions
from femstudio.ui.shell.log_dock import LogDock
from femstudio.ui.shell.menu_bar import MainMenuBar
from femstudio.ui.shell.properties_dock import PropertiesDock
from femstudio.ui.shell.scene_dock import SceneDock
from femstudio.ui.shell.status_bar import StatusPanel
from femstudio.ui.shell.viewport import TAB_FOR_STEP, Viewport
from femstudio.ui.shell.workflow_bar import WorkflowBar
from femstudio.ui.theme import stylesheet, zoom
from femstudio.ui.theme import tokens as t

TITLE = "FEM Studio"
DEFAULT_BACKEND = "mock"  # until the C++ solver has its command-line interface


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
        self.runner = Runner()
        self._files = FileActions(self, self.session)

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
        self.workflow.set_backend(DEFAULT_BACKEND)
        self.properties.set_backend(self.workflow.backend())
        self._connect()
        self._update_run_enabled()
        self.reset_layout()
        self._apply_zoom()
        self._on_step(self.workflow.step())

    def _connect(self) -> None:
        self.workflow.stepChanged.connect(self._on_step)
        self.workflow.backendChanged.connect(self.properties.set_backend)
        self.workflow.backendChanged.connect(lambda _name: self._update_run_enabled())
        self.workflow.runRequested.connect(self.start_or_stop)
        self.scene_dock.selectionChanged.connect(self._on_selection)

        menu = self.menu
        menu.newSceneRequested.connect(self.new_scene)
        menu.openFileRequested.connect(self._files.choose_file)
        menu.openFolderRequested.connect(self._files.choose_folder)
        menu.saveRequested.connect(self.save)
        menu.saveAsRequested.connect(self._files.choose_save_path)
        menu.undoRequested.connect(self.session.undo)
        menu.redoRequested.connect(self.session.redo)
        menu.quitRequested.connect(self.close)
        menu.runRequested.connect(self.start_or_stop)
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
        session.runsChanged.connect(self._show_runs)

        runner = self.runner
        runner.started.connect(self._on_run_started)
        runner.finished.connect(self._on_run_finished)
        runner.logLine.connect(self.log.append_line)

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
        stylesheet.apply(self, factor)
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
        if self.runner.busy and not self.ask_stop_solve():
            event.ignore()
            return
        if not self._files.confirm_discard():
            event.ignore()
            return
        self.runner.stop()
        if not self.runner.wait():
            self.log.append_line("[run] the solver is still running; close again when it ends")
            event.ignore()
            return
        self.viewport.close_views()
        self.session.close()
        super().closeEvent(event)

    @property
    def document(self) -> Document | None:
        return self.session.document

    # -- files and the scene being edited

    def ask_unsaved(self) -> str:
        """Ask what to do with unsaved edits: "save", "discard" or "cancel"."""
        buttons = QMessageBox.StandardButton
        box = QMessageBox(self)
        box.setWindowTitle("Unsaved changes")
        box.setText(f"Save the changes to {self.session.document.source.name}?")
        box.setStandardButtons(buttons.Save | buttons.Discard | buttons.Cancel)
        box.setDefaultButton(buttons.Save)
        answer = box.exec()
        return {buttons.Save: "save", buttons.Discard: "discard"}.get(answer, "cancel")

    def ask_stop_solve(self) -> bool:
        """Ask whether to stop the running solve to close the window."""
        buttons = QMessageBox.StandardButton
        box = QMessageBox(self)
        box.setWindowTitle("Solve running")
        box.setText("A solve is running. Stop it and close?")
        box.setStandardButtons(buttons.Yes | buttons.Cancel)
        box.setDefaultButton(buttons.Cancel)
        return box.exec() == buttons.Yes

    def open_path(self, path: Path) -> bool:
        """Open a project folder, `scene.json`, `.msh` or `.geo`; the reason is shown on failure."""
        return self._files.open_path(path)

    def new_scene(self) -> bool:
        return self._files.new_scene()

    def save(self, path: Path | None = None) -> bool:
        """Save into the project, to `path`, or ask for a name when the scene has none yet."""
        return self._files.save(path)

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
        self.scene_dock.set_document(
            document, problem_type, keep_selection=keep, runs=self.session.runs()
        )
        self.properties.set_document(document, keep_selection=keep)
        self.viewport.set_document(document, reset_view)
        self.status.set_document(document)
        self.menu.set_saveable(document is not None and document.scene is not None)
        self._update_run_enabled()
        self._update_title()
        if document is not None and reset_view:
            if document.mesh is None:
                self.log.append_line(f"[mesh] not built: {document.mesh_error}")
            else:
                mesh = document.mesh
                self.log.append_line(f"[open] {mesh.n_nodes} nodes, {mesh.n_triangles} triangles")

    # -- solving

    def _backend(self):
        try:
            return backends.get(self.workflow.backend())
        except KeyError:
            return None

    def _update_run_enabled(self) -> None:
        if self.runner.busy:
            self.workflow.set_run_enabled(True, "Stop the solve.")
            self.menu.set_run_enabled(True)
            return
        reason = why_not_runnable(self.session.document, self.status.findings(), self._backend())
        self.workflow.set_run_enabled(reason is None, reason or "Solve the scene.")
        self.menu.set_run_enabled(reason is None)

    def start_or_stop(self) -> None:
        """Run the scene on the chosen backend, or stop the solve that is running."""
        if self.runner.busy:
            self.runner.stop()
            return
        backend = self._backend()
        reason = why_not_runnable(self.session.document, self.status.findings(), backend)
        if reason is not None:
            self.log.append_line(f"[run] not started: {reason}")
            return
        try:
            plan = self.session.plan_run()
        except (RunRefused, OSError) as error:
            self.log.append_line(f"[run] not started: {error}")
            return
        self.runner.start(plan, backend)

    def _on_run_started(self, number: int) -> None:
        self.workflow.set_running(True)
        self.menu.set_running(True)
        self.status.set_run_state(f"Solving run {number}...")
        self.log.append_line(f"[run] run {number} started on {self.workflow.backend()}")
        self._show_runs()
        self._update_run_enabled()

    def is_solving(self) -> bool:
        return self.runner.busy

    def _on_run_finished(self, number: int, state: str, message: str) -> None:
        self.workflow.set_running(False)
        self.menu.set_running(False)
        self.status.set_run_state(f"Run {number}: {state}")
        suffix = f": {message}" if message else ""
        self.log.append_line(f"[run] run {number} {state}{suffix}")
        self._show_runs()
        self._update_run_enabled()
        if state == "failed":
            self.report_error(f"Run {number} failed", message)

    def _show_runs(self) -> None:
        self.scene_dock.set_runs(self.session.runs())

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


def run(argv: list[str] | None = None) -> int:
    """Open the window, and a file if one is given, then block until it is closed."""
    arguments = sys.argv if argv is None else argv
    app = QApplication(arguments)
    window = MainWindow()
    app.aboutToQuit.connect(window.viewport.close_views)
    window.show()
    if len(arguments) > 1:
        window.open_path(Path(arguments[1]))
    return app.exec()
