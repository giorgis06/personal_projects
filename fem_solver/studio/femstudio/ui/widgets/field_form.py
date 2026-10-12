from collections.abc import Mapping

from PySide6.QtWidgets import QVBoxLayout, QWidget

from femstudio.physics.base import FieldSpec
from femstudio.ui.theme import tokens as t
from femstudio.ui.theme import zoom
from femstudio.ui.widgets.expression_edit import ExpressionEdit
from femstudio.ui.widgets.number_edit import NumberEdit
from femstudio.ui.widgets.readouts import label
from femstudio.ui.widgets.tensor_edit import TensorEdit


def field_title(spec: FieldSpec) -> str:
    return f"{spec.label} [{spec.unit}]" if spec.unit else spec.label


class FieldForm(QWidget):
    """One editor per field, picked by the field's kind; a title above each, in its unit."""

    def __init__(self, specs: tuple[FieldSpec, ...], values: Mapping) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.apply_zoom()
        self._specs = specs
        self._editors: dict[str, QWidget] = {}
        for spec in specs:
            value = values.get(spec.name, spec.default)
            if spec.kind == "tensor":
                editor: QWidget = TensorEdit(value)
            elif spec.kind == "number":
                editor = NumberEdit(float(value))
            else:
                editor = ExpressionEdit(str(value))
            self._editors[spec.name] = editor
            self._layout.addWidget(label(field_title(spec), "key"))
            self._layout.addWidget(editor)

    def apply_zoom(self) -> None:
        self._layout.setSpacing(zoom.px(t.GAP))

    def editor(self, name: str) -> QWidget:
        return self._editors[name]

    def values(self) -> dict:
        """The values as the scene stores them: numbers, matrices, expression text."""
        result = {}
        for spec in self._specs:
            editor = self._editors[spec.name]
            if isinstance(editor, TensorEdit):
                result[spec.name] = editor.value()
            elif isinstance(editor, NumberEdit):
                result[spec.name] = editor.value()
            else:
                result[spec.name] = editor.text()
        return result

    def problems(self) -> list[str]:
        """The expression fields that do not parse, as `Title: reason`."""
        return [
            f"{field_title(spec)}: {editor.error()}"
            for spec in self._specs
            if isinstance(editor := self._editors[spec.name], ExpressionEdit)
            and not editor.is_valid()
        ]
