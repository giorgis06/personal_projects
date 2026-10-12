"""Edit operations on a Scene. Each raises EditError and leaves the scene unchanged when refused."""

import math
from collections.abc import Iterable

from femstudio.core.scene.boundary import (
    DEFAULT_BOUNDARY_NAME,
    Between,
    Boundary,
    BoundaryCondition,
    Curve,
    Outline,
    Side,
)
from femstudio.core.scene.operations import (
    Area,
    Operation,
    difference,
    intersection,
    leaves,
    union,
)
from femstudio.core.scene.region import Region
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.shapes import Circle, Polygon, Rectangle, Shape

OPERATIONS = {"union": union, "difference": difference, "intersection": intersection}
SHAPE_KINDS = ("circle", "rectangle", "polygon")
Operand = tuple[str | None, str]  # (operation, shape name); the first operation is None


class EditError(ValueError):
    """The edit was refused; the message says why."""


def unique_name(taken: Iterable[str], base: str) -> str:
    """`base`, or `base_2`, `base_3`... when it is taken."""
    taken = set(taken)
    if base not in taken:
        return base
    number = 2
    while f"{base}_{number}" in taken:
        number += 1
    return f"{base}_{number}"


def _check_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise EditError("a name cannot be empty")
    if name == DEFAULT_BOUNDARY_NAME:
        raise EditError(f"'{name}' is reserved")
    return name


def _check_shape_name(scene: Scene, name: str, current: str | None = None) -> str:
    name = _check_name(name)
    if name != current and any(s.name == name for s in scene.shapes):
        raise EditError(f"a shape named '{name}' already exists")
    return name


def _check_physical_name(scene: Scene, name: str, current: str | None = None) -> str:
    """Regions and boundaries share one namespace, as in the mesh file."""
    name = _check_name(name)
    taken = [r.name for r in scene.regions] + [b.name for b in scene.boundaries]
    if name != current and name in taken:
        raise EditError(f"a region or boundary named '{name}' already exists")
    return name


def new_shape(scene: Scene, kind: str) -> Shape:
    """A default shape of `kind` with a free name; it is not added to the scene."""
    if kind not in SHAPE_KINDS:
        raise EditError(f"unknown shape kind '{kind}'")
    name = unique_name((s.name for s in scene.shapes), kind)
    if kind == "circle":
        return Circle(name, (0.0, 0.0), 1.0)
    if kind == "rectangle":
        return Rectangle(name, (0.0, 0.0), 1.0, 1.0)
    return Polygon(name, ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)))


def add_shape(scene: Scene, shape: Shape) -> Shape:
    _check_shape_name(scene, shape.name)
    scene.shapes.append(shape)
    return shape


def _finite(values: Iterable[float], what: str) -> None:
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
        raise EditError(f"{what} must be finite numbers")


def update_shape(scene: Scene, name: str, **fields) -> Shape:
    """Change a shape's parameters in place, so regions built from it follow."""
    shape = scene.shape(name) if any(s.name == name for s in scene.shapes) else None
    if shape is None:
        raise EditError(f"no shape named '{name}'")
    allowed = {
        Circle: {"center", "radius"},
        Rectangle: {"corner", "width", "height"},
        Polygon: {"points"},
    }[type(shape)]
    unknown = set(fields) - allowed
    if unknown:
        raise EditError(f"a {type(shape).__name__.lower()} has no {', '.join(sorted(unknown))}")
    for key, value in fields.items():
        if key in ("center", "corner"):
            _finite(value, key)
            value = (float(value[0]), float(value[1]))
        elif key == "points":
            points = tuple((float(x), float(y)) for x, y in value)
            _finite([c for p in points for c in p], "points")
            if len(points) < 3:
                raise EditError("a polygon needs at least three points")
            value = points
        else:
            _finite([value], key)
            if value <= 0:
                raise EditError(f"{key} must be positive")
            value = float(value)
        setattr(shape, key, value)
    return shape


def rename_shape(scene: Scene, old: str, new: str) -> None:
    shape = next((s for s in scene.shapes if s.name == old), None)
    if shape is None:
        raise EditError(f"no shape named '{old}'")
    new = _check_shape_name(scene, new, current=old)
    shape.name = new
    for boundary in scene.boundaries:
        if isinstance(boundary.curve, (Outline, Side)) and boundary.curve.shape == old:
            boundary.curve.shape = new


def rename_region(scene: Scene, old: str, new: str) -> None:
    region = next((r for r in scene.regions if r.name == old), None)
    if region is None:
        raise EditError(f"no region named '{old}'")
    new = _check_physical_name(scene, new, current=old)
    region.name = new
    for boundary in scene.boundaries:
        curve = boundary.curve
        if isinstance(curve, Between):
            curve.first = new if curve.first == old else curve.first
            curve.second = new if curve.second == old else curve.second


def rename_boundary(scene: Scene, old: str, new: str) -> None:
    boundary = next((b for b in scene.boundaries if b.name == old), None)
    if boundary is None:
        raise EditError(f"no boundary named '{old}'")
    boundary.name = _check_physical_name(scene, new, current=old)


def shape_users(scene: Scene, name: str) -> list[str]:
    """What uses a shape, as 'region x' and 'boundary y' strings."""
    users = []
    for region in scene.regions:
        if any(leaf.name == name for leaf in leaves(region.area)):
            users.append(f"region '{region.name}'")
    for boundary in scene.boundaries:
        curve = boundary.curve
        if isinstance(curve, (Outline, Side)) and curve.shape == name:
            users.append(f"boundary '{boundary.name}'")
    return users


def remove_shape(scene: Scene, name: str) -> None:
    shape = next((s for s in scene.shapes if s.name == name), None)
    if shape is None:
        raise EditError(f"no shape named '{name}'")
    users = shape_users(scene, name)
    if users:
        raise EditError(f"'{name}' is used by {', '.join(users)}")
    scene.shapes.remove(shape)


def remove_region(scene: Scene, name: str) -> None:
    region = next((r for r in scene.regions if r.name == name), None)
    if region is None:
        raise EditError(f"no region named '{name}'")
    users = [
        f"boundary '{b.name}'"
        for b in scene.boundaries
        if isinstance(b.curve, Between) and name in (b.curve.first, b.curve.second)
    ]
    if users:
        raise EditError(f"'{name}' is used by {', '.join(users)}")
    scene.regions.remove(region)


def remove_boundary(scene: Scene, name: str) -> None:
    boundary = next((b for b in scene.boundaries if b.name == name), None)
    if boundary is None:
        raise EditError(f"no boundary named '{name}'")
    scene.boundaries.remove(boundary)


def build_area(scene: Scene, operands: list[Operand]) -> Area:
    """Fold `[(None, 'a'), ('difference', 'b'), ('union', 'c')]` left to right: ((a - b) | c)."""
    if not operands:
        raise EditError("a region needs at least one shape")
    by_name = {s.name: s for s in scene.shapes}
    result: Area | None = None
    for operation, name in operands:
        if name not in by_name:
            raise EditError(f"no shape named '{name}'")
        if result is None:
            result = by_name[name]
        elif operation not in OPERATIONS:
            raise EditError(f"unknown operation '{operation}'")
        else:
            result = OPERATIONS[operation](result, by_name[name])
    return result


def area_operands(area: Area) -> list[Operand] | None:
    """The inverse of `build_area`; None for an area that is not such a chain."""
    if isinstance(area, Operation):
        if len(area.operands) != 2 or isinstance(area.operands[1], Operation):
            return None
        head = area_operands(area.operands[0])
        if head is None:
            return None
        return [*head, (area.kind, area.operands[1].name)]
    return [(None, area.name)]


def add_region(
    scene: Scene, name: str, operands: list[Operand], material: dict | None = None
) -> Region:
    name = _check_physical_name(scene, name)
    region = Region(name, build_area(scene, operands), dict(material or {}))
    scene.regions.append(region)
    return region


def set_region_area(scene: Scene, name: str, operands: list[Operand]) -> None:
    region = next((r for r in scene.regions if r.name == name), None)
    if region is None:
        raise EditError(f"no region named '{name}'")
    region.area = build_area(scene, operands)


def _check_curve(scene: Scene, curve: Curve) -> None:
    if isinstance(curve, Between):
        names = {r.name for r in scene.regions}
        for name in (curve.first, curve.second):
            if name not in names:
                raise EditError(f"no region named '{name}'")
        if curve.first == curve.second:
            raise EditError("a boundary between regions needs two different regions")
        return
    shapes = {s.name: s for s in scene.shapes}
    if curve.shape not in shapes:
        raise EditError(f"no shape named '{curve.shape}'")
    if isinstance(curve, Side) and curve.side not in shapes[curve.shape].sides:
        raise EditError(f"shape '{curve.shape}' has no side '{curve.side}'")


def add_boundary(
    scene: Scene, name: str, curve: Curve, condition: BoundaryCondition | None = None
) -> Boundary:
    name = _check_physical_name(scene, name)
    _check_curve(scene, curve)
    boundary = Boundary(name, curve, condition)
    scene.boundaries.append(boundary)
    return boundary


def set_boundary_curve(scene: Scene, name: str, curve: Curve) -> None:
    boundary = next((b for b in scene.boundaries if b.name == name), None)
    if boundary is None:
        raise EditError(f"no boundary named '{name}'")
    _check_curve(scene, curve)
    boundary.curve = curve
