from PySide6.QtWidgets import QLineEdit

from femstudio.core.expressions.grammar import ExpressionError, parse


class ExpressionEdit(QLineEdit):
    """A line of text in the expression language; it marks itself when the text does not parse."""

    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        self.textChanged.connect(self._check)
        self._error = ""
        self._check(text)

    def _check(self, text: str) -> None:
        try:
            parse(text)
            self._error = ""
        except ExpressionError as error:
            self._error = str(error)
        self.setProperty("state", "invalid" if self._error else "")
        self.setToolTip(self._error)
        self.style().unpolish(self)
        self.style().polish(self)

    def is_valid(self) -> bool:
        return not self._error

    def error(self) -> str:
        return self._error
