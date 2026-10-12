from PySide6.QtWidgets import QVBoxLayout, QWidget

from femstudio.core.project.document import Document
from femstudio.core.scene.boundary import DEFAULT_BOUNDARY_NAME, Between, Outline, Side
from femstudio.core.scene.operations import Operation
from femstudio.core.scene.shapes import Circle, Polygon, Rectangle
from femstudio.ui.widgets.readouts import PairsGrid, Section

OPERATORS = {"union": "|", "difference": "-", "intersection": "&"}


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


def _shape_rows(shape) -> list[tuple[str, str]]:
    if isinstance(shape, Circle):
        return [("type", "circle"), ("center", f"{shape.center}"), ("radius", f"{shape.radius:g}")]
    if isinstance(shape, Rectangle):
        return [
            ("type", "rectangle"),
            ("corner", f"{shape.corner}"),
            ("width", f"{shape.width:g}"),
            ("height", f"{shape.height:g}"),
            ("sides", ", ".join(shape.sides)),
        ]
    if isinstance(shape, Polygon):
        return [
            ("type", "polygon"),
            ("points", f"{len(shape.points)}"),
            ("sides", ", ".join(shape.sides)),
        ]
    return [("type", type(shape).__name__)]


class GeometryPanel(QWidget):
    """The geometry of what is selected, or of the whole scene."""

    def __init__(self) -> None:
        super().__init__()
        self._grid = PairsGrid()
        self._section = Section("Geometry", self._grid)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._section)
        layout.addStretch(1)

    def rows(self) -> list[tuple[str, str]]:
        return self._grid.rows

    def update_view(self, document: Document | None, kind: str, name: str) -> None:
        rows: list[tuple[str, str]] = []
        scene = document.scene if document is not None else None
        if document is None:
            rows = [("open", "nothing")]
        elif scene is not None and kind == "shape":
            rows = _shape_rows(scene.shape(name))
        elif scene is not None and kind == "region":
            rows = [("area", describe_area(scene.region(name).area))]
        elif scene is not None and kind == "boundary" and name == DEFAULT_BOUNDARY_NAME:
            rows = [("curve", "outer edges no boundary names")]
        elif scene is not None and kind == "boundary":
            rows = [("curve", describe_curve(scene.boundary(name).curve))]
        elif scene is not None:
            rows = [
                ("shapes", str(len(scene.shapes))),
                ("regions", str(len(scene.regions))),
                ("boundaries", str(len(scene.boundaries))),
            ]
        else:
            rows = [
                ("regions", str(len(document.mesh.regions))),
                ("boundaries", str(len(document.mesh.boundaries))),
            ]
            if not document.mesh.regions and not document.mesh.boundaries:
                rows.append(("note", "this mesh names no regions or boundaries"))
        heading = {"shape": "Shape", "region": "Region", "boundary": "Boundary"}.get(kind)
        self._section.set_heading(f"{heading}: {name}" if heading and scene else "Scene")
        self._grid.set_rows(rows)
