from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QLineEdit


class NumberEdit(QLineEdit):
    """A real number as text, so `8.85e-12` and `1e6` fit without a spin box's fixed digits."""

    def __init__(self, value: float = 0.0) -> None:
        super().__init__()
        validator = QDoubleValidator(self)
        validator.setNotation(QDoubleValidator.Notation.ScientificNotation)
        self.setValidator(validator)
        self.set_value(value)

    def set_value(self, value: float) -> None:
        self.setText(f"{value:g}")

    def value(self) -> float:
        """The number typed; an unfinished entry such as `-` or an empty box counts as 0."""
        try:
            return float(self.text())
        except ValueError:
            return 0.0
