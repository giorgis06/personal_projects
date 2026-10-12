import pyvista as pv
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from femstudio.ui.theme import tokens as t

HEADLESS_PLATFORMS = ("offscreen", "minimal")  # Qt platforms with no display to draw on


class PlotterView(QWidget):
    """A widget that owns one PyVista plotter and a note line above it.

    On a platform with no display the plotter is off screen, so the scene is still built and can
    be rendered; if no OpenGL is usable the window still opens, with a message in place.
    """

    def __init__(self, lazy: bool = False) -> None:
        """With `lazy` the plotter is made when the view is first shown, not before.

        Each plotter on a real display holds an OpenGL context, so a tab nobody opens costs none.
        """
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._layout = layout
        self._note = QLabel()
        self._note.setProperty("role", "note")
        self._note.setWordWrap(True)
        self._note.hide()
        layout.addWidget(self._note)
        self._plotter = None
        self._made = False
        if not lazy:
            self._make_plotter()

    def _make_plotter(self) -> None:
        self._made = True
        layout = self._layout
        try:
            if QGuiApplication.platformName() in HEADLESS_PLATFORMS:
                self._plotter = pv.Plotter(off_screen=True)
                self._plotter.set_background(t.STAGE)
                note = QLabel("3D drawing is built off screen on this platform.")
                note.setObjectName("placeholder")
                layout.addWidget(note)
            else:
                from pyvistaqt import QtInteractor

                self._plotter = QtInteractor(self)
                self._plotter.set_background(t.STAGE)
                layout.addWidget(self._plotter.interactor)
        except Exception as error:  # no usable OpenGL: the window still opens
            note = QLabel(f"3D drawing is not available here: {error}")
            note.setObjectName("placeholder")
            layout.addWidget(note)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._made:
            self._make_plotter()
            self._plotter_ready()

    def _plotter_ready(self) -> None:
        """Called once, when a lazy view has made its plotter; draw what was waiting."""

    @property
    def can_draw(self) -> bool:
        return self._plotter is not None

    def note(self) -> str:
        return self._note.text()

    def _set_note(self, text: str) -> None:
        self._note.setText(text)
        self._note.setVisible(bool(text))

    def close_plotter(self) -> None:
        """Stop and release the 3D widget; a second call, or a late render, does nothing."""
        plotter, self._plotter = self._plotter, None
        self._made = True  # a closed view is not made again by a late show
        self._release()
        if plotter is not None:
            plotter.close()

    def _release(self) -> None:
        """Forget what was drawn; a view overrides this to drop its own references."""
