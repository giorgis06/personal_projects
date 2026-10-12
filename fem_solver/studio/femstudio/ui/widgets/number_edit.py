import math

from PySide6.QtCore import QLocale
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QLineEdit

NOT_A_NUMBER = "not a number"


def _plain_locale() -> QLocale:
    """Digits and a point, whatever the machine's locale; no group separator."""
    locale = QLocale.c()
    locale.setNumberOptions(QLocale.NumberOption.RejectGroupSeparator)
    return locale


class NumberEdit(QLineEdit):
    """A real number as text, so `8.85e-12` and `1e6` fit without a spin box's fixed digits.

    Text that is not a number marks the box; `value()` then raises rather than guess.
    """

    def __init__(self, value: float = 0.0) -> None:
        super().__init__()
        validator = QDoubleValidator(self)
        validator.setNotation(QDoubleValidator.Notation.ScientificNotation)
        validator.setLocale(_plain_locale())
        self.setValidator(validator)
        self.textChanged.connect(self._mark)
        self.set_value(value)

    def set_value(self, value: float) -> None:
        self.setText(f"{value:g}")
        self._mark(self.text())

    def _reading(self) -> float | None:
        try:
            number = float(self.text())
        except ValueError:
            return None
        return number if math.isfinite(number) else None

    def _mark(self, _text: str) -> None:
        invalid = self._reading() is None
        self.setProperty("state", "invalid" if invalid else "")
        self.setToolTip(NOT_A_NUMBER if invalid else "")
        self.style().unpolish(self)
        self.style().polish(self)

    def is_valid(self) -> bool:
        return self._reading() is not None

    def error(self) -> str:
        return "" if self.is_valid() else NOT_A_NUMBER

    def value(self) -> float:
        number = self._reading()
        if number is None:
            raise ValueError(NOT_A_NUMBER)
        return number
