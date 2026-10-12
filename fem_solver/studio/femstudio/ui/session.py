import copy
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from PySide6.QtCore import QObject, Signal

from femstudio.core.project.document import (
    Document,
    DocumentError,
    check_mesh_size,
    document_from_scene,
    open_document,
)
from femstudio.core.project.project import Project
from femstudio.core.project.run import Run
from femstudio.core.scene.editing import EditError
from femstudio.core.scene.history import History
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.serialization import save_scene
from femstudio.physics import registry as physics
from femstudio.physics.base import SolverSettings

T = TypeVar("T")
UNTITLED = Path("untitled.scene.json")
SCRATCH_PROJECT = "runs-project"


class RunRefused(ValueError):
    """There is nothing to solve yet; the message says why."""


@dataclass(frozen=True)
class RunPlan:
    """Everything a solve needs, fixed when Run is pressed: later edits do not reach it."""

    run: Run
    scene: Scene
    size: float
    settings: SolverSettings


class Session(QObject):
    """What is open and what can be done to it: edits, undo, saving, re-meshing after a change."""

    documentChanged = Signal(object, bool)  # the Document or None, and whether to reset the view
    historyChanged = Signal()
    dirtyChanged = Signal(bool)
    selectionRequested = Signal(str, str)
    editRefused = Signal(str)
    runsChanged = Signal()
    settingsChanged = Signal()
    errorRaised = Signal(str, str)
    logLine = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._workdir = tempfile.TemporaryDirectory(prefix="femstudio-")
        self._document: Document | None = None
        self._dirty = False
        self._mesh_size: float | None = None
        self._settings = SolverSettings()
        self._scratch: Project | None = None
        self.history = History()

    def close(self) -> None:
        self._workdir.cleanup()

    @property
    def document(self) -> Document | None:
        return self._document

    @property
    def scene(self) -> Scene | None:
        return self._document.scene if self._document is not None else None

    @property
    def dirty(self) -> bool:
        return self._dirty

    @property
    def mesh_size(self) -> float | None:
        """The element size chosen, or None for the default one."""
        return self._mesh_size

    @property
    def settings(self) -> SolverSettings:
        return self._settings

    def set_settings(self, settings: SolverSettings) -> None:
        self._settings = settings
        self.settingsChanged.emit()

    def set_mesh_size(self, size: float | None) -> bool:
        """Re-mesh the preview at `size` (None: the default). Not an edit: it is not undoable."""
        scene = self.scene
        if scene is None:
            return False
        if size is not None:
            try:
                check_mesh_size(scene, size)
            except DocumentError as error:
                self.editRefused.emit(str(error))
                return False
        self._mesh_size = size
        self.logLine.emit(f"[mesh] element size {'default' if size is None else f'{size:g}'}")
        self._remesh(scene)
        return True

    def runs(self) -> list[Run]:
        """The runs of the open project, or of this session's scratch project."""
        document = self._document
        if document is not None and document.project is not None:
            return document.project.runs()
        return self._scratch.runs() if self._scratch is not None else []

    def plan_run(self) -> RunPlan:
        """Fix the inputs of a solve and make its run folder.

        A scene opened outside a project keeps its runs in the session's temporary folder, which
        goes when the window closes.
        """
        document = self._document
        if document is None or document.scene is None:
            raise RunRefused("there is no scene to solve")
        if document.mesh is None or document.size is None:
            raise RunRefused(f"the scene has no mesh: {document.mesh_error}")
        scene = copy.deepcopy(document.scene)
        try:
            physics.get(scene.problem_type)
        except KeyError as error:
            raise RunRefused(str(error.args[0])) from None
        project = document.project
        if project is None:
            if self._scratch is None:
                folder = Path(self._workdir.name) / SCRATCH_PROJECT
                self._scratch = Project.create(folder, scene)
            project = self._scratch
        run = project.new_run()
        save_scene(scene, run.scene_path)
        return RunPlan(run, scene, document.size, self._settings)

    def _reset_scratch(self) -> None:
        if self._scratch is not None:
            shutil.rmtree(self._scratch.folder, ignore_errors=True)
            self._scratch = None

    def _set_dirty(self, dirty: bool) -> None:
        if dirty != self._dirty:
            self._dirty = dirty
            self.dirtyChanged.emit(dirty)

    def _show(self, document: Document | None, reset_view: bool) -> None:
        self._document = document
        self.documentChanged.emit(document, reset_view)

    def open_path(self, path: Path) -> bool:
        """Open a project folder, `scene.json`, `.msh` or `.geo`; on failure say why, carry on."""
        path = Path(path)
        self.logLine.emit(f"[open] {path}")
        try:
            document = open_document(path, Path(self._workdir.name), self.logLine.emit)
        except (ValueError, OSError) as error:
            self.logLine.emit(f"[error] {error}")
            self.errorRaised.emit(f"Cannot open {path.name}", str(error))
            return False
        self._started(document)
        return True

    def new_scene(self, problem_type: str) -> None:
        """An empty scene, kept as `untitled` until it is saved."""
        document = document_from_scene(
            Scene(problem_type), UNTITLED, Path(self._workdir.name), None, self.logLine.emit
        )
        self._started(document)

    def _started(self, document: Document) -> None:
        """A different document replaces what was open: its history, size and runs go."""
        self._mesh_size = None
        self._reset_scratch()
        self.history.clear()
        self.historyChanged.emit()
        self._set_dirty(False)
        self._show(document, True)
        self.runsChanged.emit()

    def edit(self, label: str, operation: Callable[[Scene], T], geometry: bool = True) -> T | None:
        """Apply `operation` to the scene as one undoable step, then re-mesh for the preview.

        A refused edit (EditError) changes nothing and is reported through `editRefused`.
        `geometry=False` says the edit only changes physics values, so the mesh is kept unless
        there is none or the outer edges gain or lose their default condition.
        """
        scene = self.scene
        if scene is None:
            self.editRefused.emit("there is no scene to edit")
            return None
        self.history.record(scene, label)
        had_default = scene.default_boundary is not None
        try:
            result = operation(scene)
        except EditError as error:
            self._document.scene = self.history.rollback()
            self.editRefused.emit(str(error))
            self.logLine.emit(f"[edit] refused: {error}")
            return None
        except Exception:
            self._document.scene = self.history.rollback()
            raise
        self.logLine.emit(f"[edit] {label}")
        self._set_dirty(True)
        self.historyChanged.emit()
        unchanged = (scene.default_boundary is not None) == had_default
        if geometry or self._document.mesh is None or not unchanged:
            self._remesh(scene)
        else:
            self._show(self._document, False)
        return result

    def _remesh(self, scene: Scene) -> None:
        document = document_from_scene(
            scene,
            self._document.source,
            Path(self._workdir.name),
            self._document.project,
            size=self._mesh_size,
        )
        self._show(document, False)

    def undo(self) -> None:
        if self.scene is None or not self.history.can_undo:
            return
        label = self.history.undo_label
        scene = self.history.undo(self.scene)
        self.logLine.emit(f"[undo] {label}")
        self._finish_history_step(scene)

    def redo(self) -> None:
        if self.scene is None or not self.history.can_redo:
            return
        label = self.history.redo_label
        scene = self.history.redo(self.scene)
        self.logLine.emit(f"[redo] {label}")
        self._finish_history_step(scene)

    def _finish_history_step(self, scene: Scene) -> None:
        self._set_dirty(True)
        self.historyChanged.emit()
        self._remesh(scene)

    def request_selection(self, kind: str, name: str) -> None:
        self.selectionRequested.emit(kind, name)

    def save(self, path: Path | None = None) -> bool:
        """Write the scene: into the project it came from, else to `path`."""
        document = self._document
        if document is None or document.scene is None:
            self.errorRaised.emit("Cannot save", "there is no scene to save")
            return False
        if path is None and document.project is None and document.source == UNTITLED:
            self.errorRaised.emit("Cannot save", "this scene has no file yet: choose a name")
            return False
        try:
            if document.project is not None and path is None:
                document.project.save_scene(document.scene)
                target = document.project.folder
            else:
                target = Path(path) if path is not None else document.source
                if target.suffix != ".json":
                    raise ValueError("choose a file name ending in .json")
                save_scene(document.scene, target)
        except (ValueError, OSError) as error:
            self.errorRaised.emit("Cannot save", str(error))
            return False
        document.source = target
        self._set_dirty(False)
        self.logLine.emit(f"[save] {target}")
        self.documentChanged.emit(document, False)
        return True
