from PySide6.QtWidgets import QGridLayout, QWidget

from femstudio.ui.theme import tokens as t
from femstudio.ui.theme import zoom
from femstudio.ui.widgets.number_edit import NumberEdit


class TensorEdit(QWidget):
    """A symmetric 2x2 matrix: the lower-left entry follows the upper-right one.

    `value()` gives a plain number when the matrix is isotropic, so a scalar material stays one.
    """

    def __init__(self, value) -> None:
        super().__init__()
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self.apply_zoom()
        self._boxes = [[NumberEdit(), NumberEdit()], [NumberEdit(), NumberEdit()]]
        for row in range(2):
            for column in range(2):
                self._grid.addWidget(self._boxes[row][column], row, column)
        self._boxes[1][0].setEnabled(False)
        self._boxes[0][1].textChanged.connect(self._boxes[1][0].setText)
        self.set_value(value)

    def apply_zoom(self) -> None:
        self._grid.setSpacing(zoom.px(t.GAP))

    def set_value(self, value) -> None:
        if isinstance(value, (int, float)):
            matrix = ((float(value), 0.0), (0.0, float(value)))
        else:
            matrix = tuple(tuple(float(v) for v in row) for row in value)
        for row in range(2):
            for column in range(2):
                self._boxes[row][column].set_value(matrix[row][column])
        self._boxes[1][0].set_value(matrix[0][1])

    def value(self):
        a, b = self._boxes[0][0].value(), self._boxes[0][1].value()
        d = self._boxes[1][1].value()
        if b == 0.0 and a == d:
            return a
        return ((a, b), (b, d))

    def box(self, row: int, column: int) -> NumberEdit:
        return self._boxes[row][column]
