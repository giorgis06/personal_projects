from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QWidget,
)

from femstudio.ui.theme import tokens as t
from femstudio.ui.theme import zoom

STEPS = ("Geometry", "Physics", "Mesh", "Solve", "Results")


class WorkflowBar(QWidget):
    """The five step tabs, the backend selector and the Run button."""

    stepChanged = Signal(str)
    backendChanged = Signal(str)
    runRequested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        self._layout = layout
        self._right = QHBoxLayout()
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QToolButton] = {}
        for step in STEPS:
            button = QToolButton()
            button.setObjectName("step")
            button.setText(step)
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, name=step: self.stepChanged.emit(name))
            self._group.addButton(button)
            self._buttons[step] = button
            layout.addWidget(button)
        self._buttons[STEPS[0]].setChecked(True)
        layout.addStretch(1)
        self._right.addWidget(QLabel("Backend"))
        self._backend = QComboBox()
        self._backend.setObjectName("backend")
        self._backend.currentTextChanged.connect(self.backendChanged)
        self._right.addWidget(self._backend)
        self._run = QPushButton("Run")
        self._run.setObjectName("run")
        self._run.clicked.connect(self.runRequested)
        self._right.addWidget(self._run)
        layout.addLayout(self._right)
        self.apply_zoom()

    def apply_zoom(self) -> None:
        pad = zoom.px(t.PAD)
        self._layout.setContentsMargins(pad, 0, pad, 0)
        self._right.setSpacing(pad)

    def steps(self) -> list[str]:
        return [button.text() for button in self._group.buttons()]

    def step(self) -> str:
        return next(name for name, button in self._buttons.items() if button.isChecked())

    def set_step(self, step: str) -> None:
        """Choose a step as a click would, so the panel and viewport follow."""
        self._buttons[step].setChecked(True)
        self.stepChanged.emit(step)

    def set_backends(self, names: list[str]) -> None:
        self._backend.clear()
        self._backend.addItems(names)

    def backends(self) -> list[str]:
        return [self._backend.itemText(i) for i in range(self._backend.count())]

    def backend(self) -> str:
        return self._backend.currentText()

    def set_run_enabled(self, enabled: bool, reason: str = "") -> None:
        self._run.setEnabled(enabled)
        self._run.setToolTip(reason)

    def run_enabled(self) -> bool:
        return self._run.isEnabled()
