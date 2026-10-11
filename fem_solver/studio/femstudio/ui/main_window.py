import sys

from PySide6.QtWidgets import QApplication, QMainWindow


class MainWindow(QMainWindow):
    """The application window. The Workbench layout is added in M5."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FEM Studio")
        self.resize(1280, 800)


def run() -> int:
    """Open the window and block until it is closed."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
