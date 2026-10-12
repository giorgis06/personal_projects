from PySide6.QtWidgets import QComboBox, QVBoxLayout, QWidget

from femstudio.core.scene.boundary import BoundaryCondition
from femstudio.physics.base import BoundaryKindSpec
from femstudio.ui.theme import tokens as t
from femstudio.ui.theme import zoom
from femstudio.ui.widgets.field_form import FieldForm

MIN_CONTENTS = 12  # characters; the dock is narrow, so a long kind label is cut, not widened


class ConditionEdit(QWidget):
    """Choose a kind of condition, or none, and fill in its fields; kinds come from the problem."""

    def __init__(
        self,
        kinds: tuple[BoundaryKindSpec, ...],
        condition: BoundaryCondition | None,
        none_label: str,
    ) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.apply_zoom()
        self._kinds = kinds
        self._combo = QComboBox()
        self._combo.setObjectName("kind")
        self._combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self._combo.setMinimumContentsLength(MIN_CONTENTS)
        self._combo.addItem(none_label)
        self._combo.addItems([kind.label for kind in kinds])
        self._layout.addWidget(self._combo)
        self._forms: dict[str, FieldForm] = {}
        for kind in kinds:
            known = (
                condition.values if condition is not None and condition.kind == kind.name else {}
            )
            form = FieldForm(kind.fields, known)
            self._forms[kind.name] = form
            self._layout.addWidget(form)
        self._combo.currentIndexChanged.connect(self._show_form)
        index = next(
            (i for i, k in enumerate(kinds, 1) if condition and k.name == condition.kind), 0
        )
        self._combo.setCurrentIndex(index)
        self._show_form()

    def apply_zoom(self) -> None:
        self._layout.setSpacing(zoom.px(t.GAP))

    def _show_form(self) -> None:
        chosen = self.kind_name()
        for name, form in self._forms.items():
            form.setVisible(name == chosen)

    def kind_name(self) -> str | None:
        index = self._combo.currentIndex()
        return self._kinds[index - 1].name if index > 0 else None

    def set_kind(self, name: str | None) -> None:
        names = [k.name for k in self._kinds]
        self._combo.setCurrentIndex(names.index(name) + 1 if name is not None else 0)

    def form(self, name: str) -> FieldForm:
        return self._forms[name]

    def condition(self) -> BoundaryCondition | None:
        name = self.kind_name()
        return None if name is None else BoundaryCondition(name, self._forms[name].values())

    def problems(self) -> list[str]:
        name = self.kind_name()
        return [] if name is None else self._forms[name].problems()
