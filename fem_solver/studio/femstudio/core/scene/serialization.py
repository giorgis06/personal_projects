import json
from pathlib import Path

from femstudio.core.scene.boundary import Between, Boundary, BoundaryCondition, Curve, Outline, Side
from femstudio.core.scene.operations import Area, Operation, difference, intersection, union
from femstudio.core.scene.region import Region
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.shapes import Circle, Polygon, Rectangle, Shape

SCHEMA_VERSION = 1

_OPERATIONS = {"union": union, "difference": difference, "intersection": intersection}


class SceneFileError(ValueError):
    """The data is not a scene this version can read."""


def _point(value) -> tuple[float, float]:
    x, y = value
    return (float(x), float(y))


def _encode_shape(shape: Shape) -> dict:
    if isinstance(shape, Circle):
        return {
            "type": "circle",
            "name": shape.name,
            "center": list(shape.center),
            "radius": shape.radius,
        }
    if isinstance(shape, Rectangle):
        return {
            "type": "rectangle",
            "name": shape.name,
            "corner": list(shape.corner),
            "width": shape.width,
            "height": shape.height,
        }
    if isinstance(shape, Polygon):
        return {"type": "polygon", "name": shape.name, "points": [list(p) for p in shape.points]}
    raise SceneFileError(f"cannot save shape of type {type(shape).__name__}")


def _decode_shape(data: dict) -> Shape:
    kind = data["type"]
    name = data["name"]
    if kind == "circle":
        return Circle(name, _point(data["center"]), float(data["radius"]))
    if kind == "rectangle":
        return Rectangle(name, _point(data["corner"]), float(data["width"]), float(data["height"]))
    if kind == "polygon":
        return Polygon(name, tuple(_point(p) for p in data["points"]))
    raise SceneFileError(f"unknown shape type {kind!r}")


def _encode_area(area: Area):
    if isinstance(area, Operation):
        return {"op": area.kind, "operands": [_encode_area(o) for o in area.operands]}
    return area.name


def _decode_area(data, shapes: dict[str, Shape]) -> Area:
    if isinstance(data, str):
        if data not in shapes:
            raise SceneFileError(f"region uses unknown shape {data!r}")
        return shapes[data]
    if data["op"] not in _OPERATIONS:
        raise SceneFileError(f"unknown operation {data['op']!r}")
    return _OPERATIONS[data["op"]](*(_decode_area(o, shapes) for o in data["operands"]))


def _encode_material(material: dict) -> dict:
    return {
        key: [list(row) for row in value] if isinstance(value, tuple) else value
        for key, value in material.items()
    }


def _decode_material(data: dict) -> dict:
    return {
        key: tuple(tuple(float(v) for v in row) for row in value)
        if isinstance(value, list)
        else float(value)
        for key, value in data.items()
    }


def _encode_curve(curve: Curve) -> dict:
    if isinstance(curve, Between):
        return {"between": [curve.first, curve.second]}
    if isinstance(curve, Side):
        return {"shape": curve.shape, "side": curve.side}
    return {"shape": curve.shape}


def _decode_curve(data: dict) -> Curve:
    if "between" in data:
        first, second = data["between"]
        return Between(first, second)
    if "side" in data:
        return Side(data["shape"], data["side"])
    return Outline(data["shape"])


def _encode_condition(condition: BoundaryCondition | None):
    if condition is None:
        return None
    return {"kind": condition.kind, **condition.values}


def _decode_condition(data) -> BoundaryCondition | None:
    if data is None:
        return None
    values = {key: value for key, value in data.items() if key != "kind"}
    return BoundaryCondition(data["kind"], values)


def scene_to_dict(scene: Scene) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "problem_type": scene.problem_type,
        "shapes": [_encode_shape(s) for s in scene.shapes],
        "regions": [
            {
                "name": r.name,
                "area": _encode_area(r.area),
                "material": _encode_material(r.material),
            }
            for r in scene.regions
        ],
        "boundaries": [
            {
                "name": b.name,
                **_encode_curve(b.curve),
                "condition": _encode_condition(b.condition),
            }
            for b in scene.boundaries
        ],
        "source": dict(scene.source),
    }


def scene_from_dict(data: dict) -> Scene:
    try:
        if data["schema_version"] != SCHEMA_VERSION:
            raise SceneFileError(f"unsupported schema_version {data['schema_version']!r}")
        shapes = [_decode_shape(s) for s in data["shapes"]]
        by_name = {shape.name: shape for shape in shapes}
        regions = [
            Region(r["name"], _decode_area(r["area"], by_name), _decode_material(r["material"]))
            for r in data["regions"]
        ]
        boundaries = [
            Boundary(b["name"], _decode_curve(b), _decode_condition(b["condition"]))
            for b in data["boundaries"]
        ]
        return Scene(data["problem_type"], shapes, regions, boundaries, dict(data["source"]))
    except SceneFileError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise SceneFileError(f"malformed scene: {error!r}") from error


def save_scene(scene: Scene, path: Path) -> None:
    Path(path).write_text(json.dumps(scene_to_dict(scene), indent=2) + "\n")


def load_scene(path: Path) -> Scene:
    try:
        data = json.loads(Path(path).read_text())
    except json.JSONDecodeError as error:
        raise SceneFileError(f"not valid JSON: {error}") from error
    return scene_from_dict(data)
