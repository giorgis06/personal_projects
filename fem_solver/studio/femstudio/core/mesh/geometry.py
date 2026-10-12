import gmsh

from femstudio.core.scene.operations import Area, Operation
from femstudio.core.scene.shapes import Circle, Shape

DimTag = tuple[int, int]
SURFACE = 2
CURVE = 1


def _occ():
    return gmsh.model.occ


def _line(start, end) -> int:
    return _occ().addLine(_occ().addPoint(*start, 0.0), _occ().addPoint(*end, 0.0))


def _loop_curves(points) -> list[int]:
    corners = [_occ().addPoint(x, y, 0.0) for x, y in points]
    return [
        _occ().addLine(corners[i], corners[(i + 1) % len(corners)]) for i in range(len(corners))
    ]


def add_shape(shape: Shape) -> DimTag:
    """A new surface for the shape; each call makes an independent copy."""
    if isinstance(shape, Circle):
        x, y = shape.center
        return (SURFACE, _occ().addDisk(x, y, 0.0, shape.radius, shape.radius))
    loop = _occ().addCurveLoop(_loop_curves(shape.points))
    return (SURFACE, _occ().addPlaneSurface([loop]))


def add_area(area: Area) -> list[DimTag]:
    """The surfaces covering an area. Empty when an intersection has nothing left."""
    if not isinstance(area, Operation):
        return [add_shape(area)]
    first, *rest = area.operands
    result = add_area(first)
    for operand in rest:
        other = add_area(operand)
        if not result or not other:
            result = result if area.kind == "difference" else []
            continue
        if area.kind == "union":
            result = _occ().fuse(result, other)[0]
        elif area.kind == "difference":
            result = _occ().cut(result, other)[0]
        else:
            result = _occ().intersect(result, other)[0]
    return result


def add_outline(shape: Shape, side: str | None = None) -> list[DimTag]:
    """Curves for a shape's outline or one side; fragmenting them in makes the mesh follow."""
    if isinstance(shape, Circle):
        x, y = shape.center
        return [(CURVE, _occ().addCircle(x, y, 0.0, shape.radius))]
    if side is not None:
        i = shape.sides.index(side)
        return [(CURVE, _line(shape.points[i], shape.points[(i + 1) % len(shape.points)]))]
    return [(CURVE, tag) for tag in _loop_curves(shape.points)]
