from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QDockWidget, QMenuBar


class MainMenuBar(QMenuBar):
    """File, Edit, View, Run and Help. View lists every dock, so a closed one can come back."""

    openFileRequested = Signal()
    openFolderRequested = Signal()
    quitRequested = Signal()
    resetLayoutRequested = Signal()
    runRequested = Signal()

    def __init__(self) -> None:
        super().__init__()
        file_menu = self.addMenu("File")
        file_menu.addAction("Open file...").triggered.connect(self.openFileRequested)
        file_menu.addAction("Open project folder...").triggered.connect(self.openFolderRequested)
        file_menu.addSeparator()
        file_menu.addAction("Quit").triggered.connect(self.quitRequested)

        edit_menu = self.addMenu("Edit")
        for text in ("Undo", "Redo"):
            edit_menu.addAction(text).setEnabled(False)

        self._view = self.addMenu("View")
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

    def menu_titles(self) -> list[str]:
        return [action.text() for action in self.actions()]

    def view_titles(self) -> list[str]:
        return [action.text() for action in self._view.actions() if not action.isSeparator()]
