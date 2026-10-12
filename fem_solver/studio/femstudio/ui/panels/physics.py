from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from femstudio.core.project.document import Document
from femstudio.core.scene import physics_editing as edit
from femstudio.core.scene.boundary import DEFAULT_BOUNDARY_NAME, Between
from femstudio.physics import registry
from femstudio.physics.base import FieldSpec, ProblemType
from femstudio.ui.session import Session
from femstudio.ui.theme import tokens as t
from femstudio.ui.theme import zoom
from femstudio.ui.widgets.condition_edit import ConditionEdit
from femstudio.ui.widgets.field_form import FieldForm
from femstudio.ui.widgets.readouts import PairsGrid, Section, format_value, label

NO_CONDITION = "none (insulating)"
CONTINUOUS = "none (continuous)"
UNSET = "not set"
OUTER_EDGES_NOTE = "Outer edges no boundary names take this condition."


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
    """Edit the values of the selected region or boundary, or the source and outer edges.

    The fields and the kinds of condition come from the scene's problem type.
    """

    def __init__(self, session: Session) -> None:
        super().__init__()
        self._session = session
        self._document: Document | None = None
        self._kind = ""
        self._name = ""
        self._widgets: dict[str, QWidget] = {}
        self._rows: list[tuple[str, str]] = []
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._message = label("", "note")
        self._message.setWordWrap(True)
        self._layout.addWidget(self._message)
        self._body = QWidget()
        self._layout.addWidget(self._body)
        self._layout.addStretch(1)
        session.editRefused.connect(self._message.setText)
        session.documentChanged.connect(lambda *_: self._message.setText(""))

    # -- what the tests and the window read

    def rows(self) -> list[tuple[str, str]]:
        return list(self._rows)

    def widget(self, key: str) -> QWidget:
        return self._widgets[key]

    def message(self) -> str:
        return self._message.text()

    # -- showing the selection

    def update_view(self, document: Document | None, kind: str, name: str) -> None:
        self._document, self._kind, self._name = document, kind, name
        self._body.hide()
        self._body.deleteLater()
        self._body = QWidget()
        self._layout.insertWidget(self._layout.count() - 1, self._body)
        body = QVBoxLayout(self._body)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(zoom.px(t.SECTION_GAP))
        self._widgets, self._rows = {}, []
        problem = _problem_type(document)
        if problem is None:
            grid = PairsGrid()
            grid.set_rows([("physics", "none for this file")])
            body.addWidget(Section("Physics", grid))
            return
        scene = document.scene
        if kind == "region" and any(r.name == name for r in scene.regions):
            self._region_form(body, problem, scene.region(name))
        elif kind == "boundary" and name == DEFAULT_BOUNDARY_NAME:
            self._outer_edges_form(body, problem, scene)
            self._rows = self._condition_rows(problem, scene.default_boundary)
        elif kind == "boundary" and any(b.name == name for b in scene.boundaries):
            self._boundary_form(body, problem, scene.boundary(name))
        else:
            self._source_form(body, problem, scene)
            self._outer_edges_form(body, problem, scene)

    @staticmethod
    def _section(layout: QVBoxLayout, heading: str) -> QVBoxLayout:
        holder = QWidget()
        form = QVBoxLayout(holder)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(zoom.px(t.GAP))
        layout.addWidget(Section(heading, holder))
        return form

    def _apply_button(self, form: QVBoxLayout, key: str, action) -> None:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        button = QPushButton("Apply")
        button.setObjectName(key)
        button.clicked.connect(action)
        row_layout.addWidget(button)
        row_layout.addStretch(1)
        form.addWidget(row)
        self._widgets[key] = button

    def _region_form(self, layout: QVBoxLayout, problem: ProblemType, region) -> None:
        form = self._section(layout, f"Region: {region.name}")
        editor = FieldForm(problem.material_fields, region.material)
        form.addWidget(editor)
        self._widgets["material"] = editor
        self._apply_button(form, "apply", self.apply_region)
        for spec in problem.material_fields:
            value = region.material.get(spec.name)
            if value is not None:
                self._rows.append((spec.name, format_value(value)))

    def _boundary_form(self, layout: QVBoxLayout, problem: ProblemType, boundary) -> None:
        form = self._section(layout, f"Boundary: {boundary.name}")
        none_label = CONTINUOUS if isinstance(boundary.curve, Between) else NO_CONDITION
        editor = ConditionEdit(problem.boundary_kinds, boundary.condition, none_label)
        form.addWidget(editor)
        self._widgets["condition"] = editor
        self._apply_button(form, "apply", self.apply_boundary)
        self._rows = self._condition_rows(problem, boundary.condition)

    def _source_form(self, layout: QVBoxLayout, problem: ProblemType, scene) -> None:
        if not problem.source_fields:
            return
        form = self._section(layout, "Source")
        editor = FieldForm(problem.source_fields, scene.source)
        form.addWidget(editor)
        self._widgets["source"] = editor
        self._apply_button(form, "apply_source", self.apply_source)
        for spec in problem.source_fields:
            value = scene.source.get(spec.name, spec.default)
            self._rows.append((spec.name, _with_unit(spec, value)))

    def _outer_edges_form(self, layout: QVBoxLayout, problem: ProblemType, scene) -> None:
        form = self._section(layout, "Outer edges")
        editor = ConditionEdit(problem.boundary_kinds, scene.default_boundary, UNSET)
        form.addWidget(editor)
        self._widgets["outer"] = editor
        note = label(OUTER_EDGES_NOTE, "note")
        note.setWordWrap(True)
        form.addWidget(note)
        self._apply_button(form, "apply_outer", self.apply_outer_edges)
        default = scene.default_boundary
        self._rows.append(("outer edges", default.kind if default is not None else "must be named"))

    @staticmethod
    def _condition_rows(problem: ProblemType, condition) -> list[tuple[str, str]]:
        if condition is None:
            return [("condition", "none")]
        kind = problem.boundary_kind(condition.kind)
        rows = [("kind", kind.label if kind else condition.kind)]
        for spec in kind.fields if kind else ():
            rows.append((spec.name, _with_unit(spec, condition.values.get(spec.name, ""))))
        return rows

    # -- committing edits

    def apply_region(self) -> None:
        name = self._name
        values = self._widgets["material"].values()
        self._session.edit(
            f"edit {name}", lambda scene: edit.set_material(scene, name, values), geometry=False
        )

    def apply_boundary(self) -> None:
        name = self._name
        condition = self._widgets["condition"].condition()
        self._session.edit(
            f"edit {name}",
            lambda scene: edit.set_condition(scene, name, condition),
            geometry=False,
        )

    def apply_source(self) -> None:
        values = self._widgets["source"].values()
        self._session.edit(
            "edit source", lambda scene: edit.set_source(scene, values), geometry=False
        )

    def apply_outer_edges(self) -> None:
        condition = self._widgets["outer"].condition()
        self._session.edit(
            "edit outer edges",
            lambda scene: edit.set_default_condition(scene, condition),
            geometry=False,
        )
