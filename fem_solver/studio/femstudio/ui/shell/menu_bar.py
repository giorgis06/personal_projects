from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QDockWidget, QMenuBar


class MainMenuBar(QMenuBar):
    """File, Edit, View, Run and Help. View lists every dock, so a closed one can come back."""

    newSceneRequested = Signal()
    saveRequested = Signal()
    saveAsRequested = Signal()
    undoRequested = Signal()
    redoRequested = Signal()
    openFileRequested = Signal()
    openFolderRequested = Signal()
    quitRequested = Signal()
    resetLayoutRequested = Signal()
    runRequested = Signal()
    zoomInRequested = Signal()
    zoomOutRequested = Signal()
    zoomResetRequested = Signal()

    def __init__(self) -> None:
        super().__init__()
        file_menu = self.addMenu("File")
        new = file_menu.addAction("New scene")
        new.setShortcut(QKeySequence.StandardKey.New)
        new.triggered.connect(self.newSceneRequested)
        file_menu.addAction("Open file...").triggered.connect(self.openFileRequested)
        file_menu.addAction("Open project folder...").triggered.connect(self.openFolderRequested)
        file_menu.addSeparator()
        self._save = file_menu.addAction("Save")
        self._save.setShortcut(QKeySequence.StandardKey.Save)
        self._save.triggered.connect(self.saveRequested)
        self._save_as = file_menu.addAction("Save as...")
        self._save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self._save_as.triggered.connect(self.saveAsRequested)
        file_menu.addSeparator()
        file_menu.addAction("Quit").triggered.connect(self.quitRequested)

        edit_menu = self.addMenu("Edit")
        self._undo = edit_menu.addAction("Undo")
        self._undo.setShortcut(QKeySequence.StandardKey.Undo)
        self._undo.triggered.connect(self.undoRequested)
        self._redo = edit_menu.addAction("Redo")
        self._redo.setShortcuts([QKeySequence("Ctrl+Shift+Z"), QKeySequence("Ctrl+Y")])
        self._redo.triggered.connect(self.redoRequested)
        self.set_history(None, None)
        self.set_saveable(False)

        self._view = self.addMenu("View")
        self._view.addSeparator()
        self._zoom_in = self._view.addAction("Zoom in")
        self._zoom_in.setShortcuts([QKeySequence("Ctrl++"), QKeySequence("Ctrl+=")])
        self._zoom_in.triggered.connect(self.zoomInRequested)
        self._zoom_out = self._view.addAction("Zoom out")
        self._zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        self._zoom_out.triggered.connect(self.zoomOutRequested)
        self._zoom_reset = self._view.addAction("Reset zoom")
        self._zoom_reset.setShortcut(QKeySequence("Ctrl+0"))
        self._zoom_reset.triggered.connect(self.zoomResetRequested)
        self._view.addSeparator()
        self._reset = self._view.addAction("Reset layout")
        self._reset.triggered.connect(self.resetLayoutRequested)

        self._run_menu = self.addMenu("Run")
        self._run_action = self._run_menu.addAction("Run")
        self._run_action.triggered.connect(self.runRequested)

        help_menu = self.addMenu("Help")
        help_menu.addAction("About FEM Studio").setEnabled(False)

    def set_docks(self, docks: list[QDockWidget]) -> None:
        separator = self._reset_separator()
        for dock in docks:
            self._view.insertAction(separator, dock.toggleViewAction())

    def _reset_separator(self) -> QAction:
        return self._view.actions()[0]

    def set_run_enabled(self, enabled: bool) -> None:
        self._run_action.setEnabled(enabled)

    def set_history(self, undo_label: str | None, redo_label: str | None) -> None:
        """Enable Undo and Redo, naming the edit each would take back or bring back."""
        self._undo.setEnabled(undo_label is not None)
        self._undo.setText(f"Undo {undo_label}" if undo_label else "Undo")
        self._redo.setEnabled(redo_label is not None)
        self._redo.setText(f"Redo {redo_label}" if redo_label else "Redo")

    def set_saveable(self, saveable: bool) -> None:
        self._save.setEnabled(saveable)
        self._save_as.setEnabled(saveable)

    def edit_titles(self) -> list[str]:
        edit_menu = self.actions()[1].menu()
        return [a.text() for a in edit_menu.actions()]

    def file_titles(self) -> list[str]:
        file_menu = self.actions()[0].menu()
        return [a.text() for a in file_menu.actions() if not a.isSeparator()]

    def set_zoom_limits(self, can_zoom_in: bool, can_zoom_out: bool) -> None:
        self._zoom_in.setEnabled(can_zoom_in)
        self._zoom_out.setEnabled(can_zoom_out)

    def zoom_shortcuts(self) -> dict[str, list[str]]:
        actions = {"in": self._zoom_in, "out": self._zoom_out, "reset": self._zoom_reset}
        return {k: [s.toString() for s in a.shortcuts()] for k, a in actions.items()}

    def menu_titles(self) -> list[str]:
        return [action.text() for action in self.actions()]

    def view_titles(self) -> list[str]:
        return [action.text() for action in self._view.actions() if not action.isSeparator()]
