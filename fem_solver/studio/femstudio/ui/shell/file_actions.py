from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QWidget

from femstudio.physics import registry as physics
from femstudio.ui.session import UNTITLED, Session


class FileActions:
    """New, open and save for the window, asking what to do with unsaved edits first."""

    def __init__(self, window: QWidget, session: Session) -> None:
        self._window = window
        self._session = session

    def confirm_discard(self) -> bool:
        """True when it is fine to replace or close the scene: it is saved, or the user said so."""
        if not self._session.dirty:
            return True
        choice = self._window.ask_unsaved()
        if choice == "save":
            return self.save()
        return choice == "discard"

    def open_path(self, path: Path) -> bool:
        if not self.confirm_discard():
            return False
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            return self._session.open_path(Path(path))
        finally:
            QApplication.restoreOverrideCursor()

    def new_scene(self) -> bool:
        if not self.confirm_discard():
            return False
        types = [p.name for p in physics.available()]
        if not types:
            self._window.report_error("New scene", "no problem type is available")
            return False
        problem = types[0]
        if len(types) > 1:
            problem, chosen = QInputDialog.getItem(
                self._window, "New scene", "Problem type", types, 0, False
            )
            if not chosen:
                return False
        self._session.new_scene(problem)
        return True

    def save(self, path: Path | None = None) -> bool:
        """Save into the project, to `path`, or ask for a name when the scene has none yet."""
        document = self._session.document
        if path is None and document is not None and document.project is None:
            if document.source == UNTITLED or document.source.suffix != ".json":
                return self.choose_save_path()
        return self._session.save(path)

    def choose_save_path(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(self._window, "Save scene", "", "Scene (*.json)")
        return bool(path) and self._session.save(Path(path))

    def choose_file(self) -> None:
        text = "Scene or mesh (*.json *.msh *.geo)"
        path, _ = QFileDialog.getOpenFileName(self._window, "Open", "", text)
        if path:
            self.open_path(Path(path))

    def choose_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self._window, "Open project folder")
        if path:
            self.open_path(Path(path))
