from PySide6.QtWidgets import QVBoxLayout, QWidget

from femstudio.core.project.document import Document
from femstudio.ui.widgets.readouts import label


class ResultsPanel(QWidget):
    """Where the field display options and the probe will go."""

    def __init__(self) -> None:
        super().__init__()
        self._note = label("No result yet.", "note")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._note)
        layout.addStretch(1)

    def text(self) -> str:
        return self._note.text()

    def update_view(self, document: Document | None, kind: str, name: str) -> None:
        self._note.setText(f"{name}: no result loaded." if kind == "run" else "No result yet.")
