from collections.abc import Callable

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from femstudio.core.project.document import Document
from femstudio.core.scene import editing
from femstudio.core.scene.boundary import (
    DEFAULT_BOUNDARY_NAME,
    Between,
    Outline,
    Side,
)
from femstudio.core.scene.operations import Operation
from femstudio.core.scene.shapes import Circle, Polygon, Rectangle
from femstudio.physics import registry
from femstudio.ui.session import Session
from femstudio.ui.theme import tokens as t
from femstudio.ui.theme import zoom
from femstudio.ui.widgets.readouts import PairsGrid, Section, label

OPERATORS = {"union": "|", "difference": "-", "intersection": "&"}
OPERATION_TITLES = {"union": "add", "difference": "subtract", "intersection": "intersect"}
CURVE_KINDS = {
    "outline": "Outline of a shape",
    "side": "Side of a shape",
    "between": "Between regions",
}
CURVE_FIELDS = {
    "outline": ("shape",),
    "side": ("shape", "side"),
    "between": ("first", "second"),
}
ADD_KINDS = ("circle", "rectangle", "polygon", "region", "boundary")
LIMIT = 1e9
MIN_COMBO = 6
ADD_COLUMNS = 3


def describe_area(area) -> str:
    if isinstance(area, Operation):
        joiner = f" {OPERATORS[area.kind]} "
        return "(" + joiner.join(describe_area(o) for o in area.operands) + ")"
    return area.name


def describe_curve(curve) -> str:
    if isinstance(curve, Between):
        return f"between {curve.first} and {curve.second}"
    if isinstance(curve, Side):
        return f"side {curve.side} of {curve.shape}"
    if isinstance(curve, Outline):
        return f"outline of {curve.shape}"
    return str(curve)


def _number(value: float) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(-LIMIT, LIMIT)
    box.setDecimals(6)
    box.setSingleStep(0.1)
    box.setValue(value)
    box.setGroupSeparatorShown(False)
    return box


def _combo(items: list[str], current: str | None = None, characters: int = MIN_COMBO) -> QComboBox:
    box = QComboBox()
    box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    box.setMinimumContentsLength(characters)
    box.addItems(items)
    if current in items:
        box.setCurrentText(current)
    return box


def _points_text(points) -> str:
    return "\n".join(f"{x:g}, {y:g}" for x, y in points)


def _parse_points(text: str) -> list[tuple[float, float]]:
    points = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.replace(";", ",").split(",")
        if len(parts) != 2:
            raise editing.EditError(f"line {number}: write a point as 'x, y'")
        try:
            points.append((float(parts[0]), float(parts[1])))
        except ValueError:
            raise editing.EditError(f"line {number}: '{line.strip()}' is not two numbers") from None
    return points


class GeometryPanel(QWidget):
    """Edit the scene's shapes, regions and boundaries, one selected item at a time."""

    def __init__(self, session: Session) -> None:
        super().__init__()
        self._session = session
        self._document: Document | None = None
        self._kind = ""
        self._name = ""
        self._widgets: dict[str, QWidget] = {}
        self._operand_rows: list[tuple[QComboBox | None, QComboBox]] = []
        self._rows: list[tuple[str, str]] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._outer = outer
        self._add_buttons: dict[str, QPushButton] = {}
        add_row = QWidget()
        add_layout = QGridLayout(add_row)
        add_layout.setContentsMargins(0, 0, 0, 0)
        for index, kind in enumerate(ADD_KINDS):
            button = QPushButton(f"+ {kind}")
            button.setObjectName(f"add_{kind}")
            button.clicked.connect(lambda _checked=False, k=kind: self.add_item(k))
            self._add_buttons[kind] = button
            add_layout.addWidget(button, index // ADD_COLUMNS, index % ADD_COLUMNS)
        self._add_row = add_row
        self._add_section = Section("Add", add_row)
        outer.addWidget(self._add_section)
        self._message = label("", "note")
        self._message.setWordWrap(True)
        outer.addWidget(self._message)
        self._body = QWidget()
        outer.addWidget(self._body)
        outer.addStretch(1)
        session.editRefused.connect(self._message.setText)
        session.documentChanged.connect(lambda *_: self._message.setText(""))

    # -- what the tests and the window read

    def rows(self) -> list[tuple[str, str]]:
        return list(self._rows)

    def field(self, key: str) -> QWidget:
        return self._widgets[key]

    def message(self) -> str:
        return self._message.text()

    def can_add(self) -> bool:
        return self._document is not None and self._document.scene is not None

    # -- showing the selection

    def update_view(self, document: Document | None, kind: str, name: str) -> None:
        self._document, self._kind, self._name = document, kind, name
        editable = self.can_add()
        for button in self._add_buttons.values():
            button.setEnabled(editable)
        self._body.hide()
        self._body.deleteLater()
        self._body = QWidget()
        self._outer.insertWidget(self._outer.count() - 1, self._body)
        layout = QVBoxLayout(self._body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(zoom.px(t.SECTION_GAP))
        self._widgets, self._operand_rows, self._rows = {}, [], []
        self._row_widgets: dict[str, QWidget] = {}
        scene = document.scene if document is not None else None
        if scene is None:
            self._summary(layout, document)
        elif kind == "shape" and any(s.name == name for s in scene.shapes):
            self._shape_form(layout, scene.shape(name))
        elif kind == "region" and any(r.name == name for r in scene.regions):
            self._region_form(layout, scene, scene.region(name))
        elif kind == "boundary" and name == DEFAULT_BOUNDARY_NAME:
            self._summary(layout, document, [("curve", "outer edges no boundary names")])
        elif kind == "boundary" and any(b.name == name for b in scene.boundaries):
            self._boundary_form(layout, scene, scene.boundary(name))
        else:
            self._summary(layout, document)

    def _summary(self, layout: QVBoxLayout, document, rows=None) -> None:
        grid = PairsGrid()
        scene = document.scene if document is not None else None
        heading = "Scene"
        if rows is None:
            if document is None:
                rows = [("open", "nothing")]
            elif scene is not None:
                rows = [
                    ("shapes", str(len(scene.shapes))),
                    ("regions", str(len(scene.regions))),
                    ("boundaries", str(len(scene.boundaries))),
                ]
            else:
                mesh = document.mesh
                rows = [
                    ("regions", str(len(mesh.regions))),
                    ("boundaries", str(len(mesh.boundaries))),
                ]
                if not mesh.regions and not mesh.boundaries:
                    rows.append(("note", "this mesh names no regions or boundaries"))
                rows.append(("editing", "open a scene to edit"))
        grid.set_rows(rows)
        self._rows = rows
        layout.addWidget(Section(heading, grid))

    def _form_row(self, form: QVBoxLayout, text: str, widget: QWidget, key: str) -> None:
        row = QWidget()
        self._row_widgets[key] = row
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(label(text, "key"))
        row_layout.addWidget(widget, 1)
        form.addWidget(row)
        self._widgets[key] = widget

    def _buttons(self, form: QVBoxLayout) -> None:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        apply = QPushButton("Apply")
        apply.setObjectName("apply")
        apply.clicked.connect(self.apply)
        delete = QPushButton("Delete")
        delete.setObjectName("delete")
        delete.clicked.connect(self.delete)
        layout.addWidget(apply)
        layout.addWidget(delete)
        layout.addStretch(1)
        form.addWidget(row)
        self._widgets["apply"], self._widgets["delete"] = apply, delete

    def _section(self, layout: QVBoxLayout, heading: str) -> QVBoxLayout:
        body = QWidget()
        form = QVBoxLayout(body)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(zoom.px(t.GAP))
        layout.addWidget(Section(heading, body))
        return form

    def _shape_form(self, layout: QVBoxLayout, shape) -> None:
        form = self._section(layout, f"Shape: {shape.name}")
        self._form_row(form, "name", QLineEdit(shape.name), "name")
        if isinstance(shape, Circle):
            self._form_row(form, "center x", _number(shape.center[0]), "center_x")
            self._form_row(form, "center y", _number(shape.center[1]), "center_y")
            self._form_row(form, "radius", _number(shape.radius), "radius")
        elif isinstance(shape, Rectangle):
            self._form_row(form, "corner x", _number(shape.corner[0]), "corner_x")
            self._form_row(form, "corner y", _number(shape.corner[1]), "corner_y")
            self._form_row(form, "width", _number(shape.width), "width")
            self._form_row(form, "height", _number(shape.height), "height")
        elif isinstance(shape, Polygon):
            points = QPlainTextEdit(_points_text(shape.points))
            points.setObjectName("points")
            self._form_row(form, "points", points, "points")
        self._buttons(form)
        self._rows = [("shape", shape.name)]

    def _region_form(self, layout: QVBoxLayout, scene, region) -> None:
        form = self._section(layout, f"Region: {region.name}")
        self._form_row(form, "name", QLineEdit(region.name), "name")
        operands = editing.area_operands(region.area)
        if operands is None:
            self._form_row(form, "area", label(describe_area(region.area), "value"), "area")
            note = label("This area is not a simple chain; edit it by script.", "note")
            form.addWidget(note)
        else:
            shapes = [s.name for s in scene.shapes]
            holder = QWidget()
            holder_layout = QVBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            for index, (operation, shape) in enumerate(operands):
                self._add_operand_row(holder_layout, shapes, operation, shape, index)
            more = QToolButton()
            more.setText("+ shape")
            more.setObjectName("add_operand")
            more.clicked.connect(lambda: self._append_operand(holder_layout, shapes))
            holder_layout.addWidget(more)
            form.addWidget(label("area", "key"))
            form.addWidget(holder)
            self._widgets["add_operand"] = more
        self._buttons(form)
        self._rows = [("region", region.name)]

    def _add_operand_row(self, parent: QVBoxLayout, shapes, operation, shape, index) -> None:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        op_box = None
        if index > 0:
            titles = list(OPERATION_TITLES)
            op_box = _combo(titles, operation, max(len(title) for title in titles))
            layout.addWidget(op_box)
            self._widgets[f"operation_{index}"] = op_box
        shape_box = _combo(shapes, shape)
        layout.addWidget(shape_box, 1)
        self._widgets[f"shape_{index}"] = shape_box
        before_button = "add_operand" in self._widgets
        parent.insertWidget(parent.count() - 1 if before_button else parent.count(), row)
        self._operand_rows.append((op_box, shape_box))

    def _append_operand(self, parent: QVBoxLayout, shapes) -> None:
        index = len(self._operand_rows)
        self._add_operand_row(parent, shapes, "union", shapes[0] if shapes else "", index)

    def _boundary_form(self, layout: QVBoxLayout, scene, boundary) -> None:
        form = self._section(layout, f"Boundary: {boundary.name}")
        self._form_row(form, "name", QLineEdit(boundary.name), "name")
        curve = boundary.curve
        kind = (
            "between"
            if isinstance(curve, Between)
            else "side"
            if isinstance(curve, Side)
            else "outline"
        )
        kind_box = _combo(list(CURVE_KINDS.values()), CURVE_KINDS[kind])
        self._form_row(form, "curve", kind_box, "curve_kind")
        shapes = [s.name for s in scene.shapes]
        regions = [r.name for r in scene.regions]
        shape_name = getattr(curve, "shape", shapes[0] if shapes else "")
        self._form_row(form, "shape", _combo(shapes, shape_name), "shape")
        sides = scene.shape(shape_name).sides if shape_name in shapes else ()
        self._form_row(form, "side", _combo(list(sides), getattr(curve, "side", None)), "side")
        first = curve.first if isinstance(curve, Between) else (regions[0] if regions else "")
        second = curve.second if isinstance(curve, Between) else (regions[-1] if regions else "")
        self._form_row(form, "first region", _combo(regions, first), "first")
        self._form_row(form, "second region", _combo(regions, second), "second")
        shape_box = self._widgets["shape"]
        shape_box.currentTextChanged.connect(lambda text: self._refresh_sides(scene, text))
        kind_box.currentTextChanged.connect(lambda _text: self._show_curve_fields())
        self._show_curve_fields()
        self._buttons(form)
        self._rows = [("boundary", boundary.name)]

    def _curve_kind(self) -> str:
        chosen = self._widgets["curve_kind"].currentText()
        return next(k for k, title in CURVE_KINDS.items() if title == chosen)

    def _show_curve_fields(self) -> None:
        """Show only the fields the chosen kind of curve uses."""
        shown = CURVE_FIELDS[self._curve_kind()]
        for key in ("shape", "side", "first", "second"):
            self._row_widgets[key].setVisible(key in shown)

    def _refresh_sides(self, scene, shape_name: str) -> None:
        box = self._widgets["side"]
        box.clear()
        if any(s.name == shape_name for s in scene.shapes):
            box.addItems(list(scene.shape(shape_name).sides))

    # -- committing edits

    def add_item(self, kind: str) -> None:
        """Add a default shape, region or boundary with a free name, and select it."""
        problem = self._problem_type()

        def operation(scene):
            if kind in ("circle", "rectangle", "polygon"):
                shape = editing.new_shape(scene, kind)
                editing.add_shape(scene, shape)
                return "shape", shape.name
            if not scene.shapes:
                raise editing.EditError("add a shape first")
            if kind == "region":
                name = editing.unique_name(self._physical_names(scene), "region")
                material = {f.name: f.default for f in problem.material_fields} if problem else {}
                editing.add_region(scene, name, [(None, scene.shapes[0].name)], material)
                return "region", name
            name = editing.unique_name(self._physical_names(scene), "boundary")
            editing.add_boundary(scene, name, Outline(scene.shapes[0].name))
            return "boundary", name

        result = self._session.edit(f"add {kind}", operation)
        if result is not None:
            self._session.request_selection(*result)

    @staticmethod
    def _physical_names(scene) -> list[str]:
        return [r.name for r in scene.regions] + [b.name for b in scene.boundaries]

    def _problem_type(self):
        scene = self._session.scene
        try:
            return registry.get(scene.problem_type) if scene is not None else None
        except KeyError:
            return None

    def apply(self) -> None:
        """Commit the form as one undoable edit."""
        kind, old = self._kind, self._name
        new = self._widgets["name"].text() if "name" in self._widgets else old
        try:
            if kind == "shape":
                fields = self._shape_fields()
            elif kind == "region":
                operands = self._operands()
            elif kind == "boundary":
                curve = self._curve()
            else:
                return
        except editing.EditError as error:
            self._session.editRefused.emit(str(error))
            return

        def operation(scene):
            if kind == "shape":
                editing.update_shape(scene, old, **fields)
                editing.rename_shape(scene, old, new)
            elif kind == "region":
                if operands is not None:
                    editing.set_region_area(scene, old, operands)
                editing.rename_region(scene, old, new)
            else:
                editing.set_boundary_curve(scene, old, curve)
                editing.rename_boundary(scene, old, new)
            return kind, new.strip()

        result = self._session.edit(f"edit {kind}", operation)
        if result is not None:
            self._session.request_selection(*result)

    def _shape_fields(self) -> dict:
        shape = self._session.scene.shape(self._name)
        value = lambda key: self._widgets[key].value()  # noqa: E731
        if isinstance(shape, Circle):
            return {"center": (value("center_x"), value("center_y")), "radius": value("radius")}
        if isinstance(shape, Rectangle):
            return {
                "corner": (value("corner_x"), value("corner_y")),
                "width": value("width"),
                "height": value("height"),
            }
        return {"points": _parse_points(self._widgets["points"].toPlainText())}

    def _operands(self):
        if not self._operand_rows:
            return None
        operands = []
        for op_box, shape_box in self._operand_rows:
            operands.append((op_box.currentText() if op_box else None, shape_box.currentText()))
        return operands

    def _curve(self):
        kind = self._curve_kind()
        shape, side = self._widgets["shape"].currentText(), self._widgets["side"].currentText()
        if kind == "between":
            return Between(
                self._widgets["first"].currentText(), self._widgets["second"].currentText()
            )
        if kind == "side":
            return Side(shape, side)
        return Outline(shape)

    def delete(self) -> None:
        kind, name = self._kind, self._name
        remove: dict[str, Callable] = {
            "shape": editing.remove_shape,
            "region": editing.remove_region,
            "boundary": editing.remove_boundary,
        }
        if kind not in remove:
            return
        self._session.edit(f"delete {kind}", lambda scene: remove[kind](scene, name))
