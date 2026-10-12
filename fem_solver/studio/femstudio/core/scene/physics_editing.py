"""Edit the physics values of a Scene: materials, conditions, the source.

Which fields exist is the problem type's business; these operations check only the shape of
what is stored. An expression that does not parse is kept and reported by validation.
"""

import math
from collections.abc import Mapping

from femstudio.core.scene.boundary import BoundaryCondition
from femstudio.core.scene.editing import EditError
from femstudio.core.scene.scene import Scene


def _number(value, what: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise EditError(f"{what} must be a number") from None
    if not math.isfinite(number):
        raise EditError(f"{what} must be a finite number")
    return number


def _material_value(key: str, value):
    if isinstance(value, (int, float)):
        return _number(value, key)
    try:
        rows = [[_number(v, key) for v in row] for row in value]
    except TypeError:
        raise EditError(f"{key} must be a number or a 2x2 matrix") from None
    if len(rows) != 2 or any(len(row) != 2 for row in rows):
        raise EditError(f"{key} must be a number or a 2x2 matrix")
    return ((rows[0][0], rows[0][1]), (rows[1][0], rows[1][1]))


def _expressions(values: Mapping, what: str) -> dict[str, str]:
    if not all(isinstance(text, str) for text in values.values()):
        raise EditError(f"{what} must be written as expressions")
    return dict(values)


def set_material(scene: Scene, region: str, values: Mapping) -> None:
    """Replace a region's material values."""
    target = next((r for r in scene.regions if r.name == region), None)
    if target is None:
        raise EditError(f"no region named '{region}'")
    target.material = {key: _material_value(key, value) for key, value in values.items()}


def set_condition(scene: Scene, boundary: str, condition: BoundaryCondition | None) -> None:
    """Give a boundary a condition, or None for the default (insulating, or continuous inside)."""
    target = next((b for b in scene.boundaries if b.name == boundary), None)
    if target is None:
        raise EditError(f"no boundary named '{boundary}'")
    target.condition = _checked(condition)


def set_default_condition(scene: Scene, condition: BoundaryCondition | None) -> None:
    """The condition for outer edges no boundary names; None leaves them unnamed."""
    scene.default_boundary = _checked(condition)


def set_source(scene: Scene, values: Mapping) -> None:
    scene.source = _expressions(values, "source values")


def _checked(condition: BoundaryCondition | None) -> BoundaryCondition | None:
    if condition is None:
        return None
    return BoundaryCondition(condition.kind, _expressions(condition.values, "boundary values"))
