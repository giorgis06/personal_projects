from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from femstudio.ui.theme import tokens as t
from femstudio.ui.theme import zoom


def label(text: str, role: str) -> QLabel:
    widget = QLabel(text)
    widget.setProperty("role", role)
    widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return widget


class PairsGrid(QWidget):
    """Rows of a muted key and a value, read-only."""

    def __init__(self) -> None:
        super().__init__()
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.apply_zoom()
        self._layout.setColumnStretch(1, 1)
        self._rows: list[tuple[str, str]] = []

    def apply_zoom(self) -> None:
        self._layout.setHorizontalSpacing(zoom.px(t.SECTION_GAP))
        self._layout.setVerticalSpacing(zoom.px(t.GAP))

    @property
    def rows(self) -> list[tuple[str, str]]:
        return list(self._rows)

    def set_rows(self, rows: list[tuple[str, str]]) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget() is not None:
                item.widget().hide()
                item.widget().deleteLater()
        self._rows = list(rows)
        for index, (key, value) in enumerate(rows):
            self._layout.addWidget(label(key, "key"), index, 0, Qt.AlignmentFlag.AlignTop)
            value_label = label(value, "value")
            value_label.setWordWrap(True)
            self._layout.addWidget(value_label, index, 1)


class MatrixReadout(QWidget):
    """A 2x2 matrix as four framed fields."""

    def __init__(self, matrix) -> None:
        super().__init__()
        self._grid = QGridLayout(self)
        grid = self._grid
        grid.setContentsMargins(0, 0, 0, 0)
        self.apply_zoom()
        for row, values in enumerate(matrix):
            for column, value in enumerate(values):
                grid.addWidget(label(f"{value:g}", "field"), row, column)

    def apply_zoom(self) -> None:
        self._grid.setSpacing(zoom.px(t.GAP))


class Section(QWidget):
    """A heading above a body widget."""

    def __init__(self, heading: str, body: QWidget) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        layout = self._layout
        layout.setContentsMargins(0, 0, 0, 0)
        self.apply_zoom()
        self._heading = label(heading, "heading")
        layout.addWidget(self._heading)
        layout.addWidget(body)

    def set_heading(self, text: str) -> None:
        self._heading.setText(text)

    def apply_zoom(self) -> None:
        self._layout.setSpacing(zoom.px(t.GAP))


def format_value(value) -> str:
    """A number as `4` or `0.25`, an isotropic 2x2 matrix as its diagonal value, text as is."""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return f"{value:g}"
    (a, b), (c, d) = value
    if b == 0 and c == 0 and a == d:
        return f"{a:g}"
    return "tensor"
