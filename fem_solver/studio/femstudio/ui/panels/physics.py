from PySide6.QtWidgets import QVBoxLayout, QWidget

from femstudio.core.project.document import Document
from femstudio.core.scene.boundary import DEFAULT_BOUNDARY_NAME
from femstudio.physics import registry
from femstudio.physics.base import FieldSpec, ProblemType
from femstudio.ui.theme import tokens as t
from femstudio.ui.widgets.readouts import MatrixReadout, PairsGrid, Section, format_value


def _problem_type(document: Document | None) -> ProblemType | None:
    if document is None or document.scene is None:
        return None
    try:
        return registry.get(document.scene.problem_type)
    except KeyError:
        return None


def _with_unit(spec: FieldSpec, value) -> str:
    return f"{format_value(value)} {spec.unit}".strip()


class PhysicsPanel(QWidget):
    """The values of the selected region or boundary, from the problem type's own fields."""

    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._body = QWidget()
        self._layout.addWidget(self._body)
        self._layout.addStretch(1)
        self._rows: list[tuple[str, str]] = []

    def rows(self) -> list[tuple[str, str]]:
        return list(self._rows)

    def update_view(self, document: Document | None, kind: str, name: str) -> None:
        self._body.deleteLater()
        self._body = QWidget()
        self._layout.insertWidget(0, self._body)
        body = QVBoxLayout(self._body)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(t.SECTION_GAP)
        self._rows = []
        problem = _problem_type(document)
        if problem is None:
            grid = PairsGrid()
            grid.set_rows([("physics", "none for this file")])
            body.addWidget(Section("Physics", grid))
            return
        scene = document.scene
        if kind == "region":
            region = scene.region(name)
            for spec in problem.material_fields:
                value = region.material.get(spec.name)
                if value is None:
                    continue
                self._rows.append((spec.name, format_value(value)))
                if isinstance(value, tuple):
                    body.addWidget(Section(f"{spec.label}", MatrixReadout(value)))
                else:
                    grid = PairsGrid()
                    grid.set_rows([(spec.name, _with_unit(spec, value))])
                    body.addWidget(Section(f"{spec.label}", grid))
            return
        grid = PairsGrid()
        rows = []
        if kind == "boundary":
            is_default = name == DEFAULT_BOUNDARY_NAME
            condition = scene.default_boundary if is_default else scene.boundary(name).condition
            if condition is None:
                rows = [("condition", "none")]
            else:
                kind_spec = problem.boundary_kind(condition.kind)
                rows = [("kind", kind_spec.label if kind_spec else condition.kind)]
                for spec in kind_spec.fields if kind_spec else ():
                    rows.append((spec.name, _with_unit(spec, condition.values.get(spec.name, ""))))
            heading = f"Boundary: {name}"
        else:
            for spec in problem.source_fields:
                rows.append(
                    (spec.name, _with_unit(spec, scene.source.get(spec.name, spec.default)))
                )
            default = scene.default_boundary
            rows.append(("outer edges", default.kind if default is not None else "must be named"))
            heading = "Source and outer edges"
        grid.set_rows(rows)
        self._rows = rows
        body.addWidget(Section(heading, grid))
