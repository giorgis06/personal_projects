import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from PySide6.QtCore import QObject, Signal

from femstudio.core.project.document import Document, document_from_scene, open_document
from femstudio.core.scene.editing import EditError
from femstudio.core.scene.history import History
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.serialization import save_scene

T = TypeVar("T")
UNTITLED = Path("untitled.scene.json")


class Session(QObject):
    """What is open and what can be done to it: edits, undo, saving, re-meshing after a change."""

    documentChanged = Signal(object, bool)  # the Document or None, and whether to reset the view
    historyChanged = Signal()
    dirtyChanged = Signal(bool)
    selectionRequested = Signal(str, str)
    editRefused = Signal(str)
    errorRaised = Signal(str, str)
    logLine = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._workdir = tempfile.TemporaryDirectory(prefix="femstudio-")
        self._document: Document | None = None
        self._dirty = False
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
        self.history.clear()
        self.historyChanged.emit()
        self._set_dirty(False)
        self._show(document, True)
        return True

    def new_scene(self, problem_type: str) -> None:
        """An empty scene, kept as `untitled` until it is saved."""
        document = document_from_scene(
            Scene(problem_type), UNTITLED, Path(self._workdir.name), None, self.logLine.emit
        )
        self.history.clear()
        self.historyChanged.emit()
        self._set_dirty(False)
        self._show(document, True)

    def edit(self, label: str, operation: Callable[[Scene], T]) -> T | None:
        """Apply `operation` to the scene as one undoable step, then re-mesh for the preview.

        A refused edit (EditError) changes nothing and is reported through `editRefused`.
        """
        scene = self.scene
        if scene is None:
            self.editRefused.emit("there is no scene to edit")
            return None
        self.history.record(scene, label)
        try:
            result = operation(scene)
        except EditError as error:
            self._document.scene = self.history.rollback()
            self.editRefused.emit(str(error))
            self.logLine.emit(f"[edit] refused: {error}")
            return None
        self.logLine.emit(f"[edit] {label}")
        self._set_dirty(True)
        self.historyChanged.emit()
        self._remesh(scene)
        return result

    def _remesh(self, scene: Scene) -> None:
        document = document_from_scene(
            scene,
            self._document.source,
            Path(self._workdir.name),
            self._document.project,
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
