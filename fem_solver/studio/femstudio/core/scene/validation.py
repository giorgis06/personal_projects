from collections import Counter
from dataclasses import dataclass
from typing import Literal

import numpy as np

from femstudio.core.expressions.grammar import ExpressionError, parse
from femstudio.core.scene.boundary import Between, Boundary, Outline
from femstudio.core.scene.operations import leaves
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.shapes import Circle, Polygon, Rectangle

SYMMETRY_TOLERANCE = 1e-12


@dataclass(frozen=True)
class Finding:
    severity: Literal["error", "warning"]
    rule: str
    subject: str
    message: str


def _error(rule: str, subject: str, message: str) -> Finding:
    return Finding("error", rule, subject, message)


def _warning(rule: str, subject: str, message: str) -> Finding:
    return Finding("warning", rule, subject, message)


def _groups(scene: Scene):
    return (("shape", scene.shapes), ("region", scene.regions), ("boundary", scene.boundaries))


def _names(scene: Scene) -> list[Finding]:
    findings = []
    for kind, items in _groups(scene):
        counts = Counter(item.name for item in items)
        for index, item in enumerate(items):
            if not item.name.strip():
                findings.append(_error("names", f"{kind} #{index + 1}", "name is empty"))
            elif counts[item.name] > 1:
                findings.append(_error("names", f"{kind} '{item.name}'", "name is not unique"))
    return findings


def _shape_parameters(scene: Scene) -> list[Finding]:
    findings = []
    for shape in scene.shapes:
        subject = f"shape '{shape.name}'"
        if isinstance(shape, Circle) and not shape.radius > 0:
            findings.append(_error("shape-parameters", subject, "radius must be positive"))
        elif isinstance(shape, Rectangle) and not (shape.width > 0 and shape.height > 0):
            message = "width and height must be positive"
            findings.append(_error("shape-parameters", subject, message))
        elif isinstance(shape, Polygon) and len(shape.points) < 3:
            findings.append(_error("shape-parameters", subject, "a polygon needs three points"))
    return findings


def _references(scene: Scene) -> list[Finding]:
    findings = []
    for region in scene.regions:
        for leaf in leaves(region.area):
            if leaf not in scene.shapes:
                name = getattr(leaf, "name", "?")
                message = f"uses shape '{name}', which is not in the scene"
                findings.append(_error("references", f"region '{region.name}'", message))
    for boundary in scene.boundaries:
        problem = _curve_problem(scene, boundary)
        if problem:
            findings.append(_error("references", f"boundary '{boundary.name}'", problem))
    return findings


def _curve_problem(scene: Scene, boundary: Boundary) -> str | None:
    curve = boundary.curve
    if isinstance(curve, Between):
        regions = {region.name for region in scene.regions}
        for name in (curve.first, curve.second):
            if name not in regions:
                return f"refers to unknown region '{name}'"
        if curve.first == curve.second:
            return "needs two different regions"
        return None
    shapes = {shape.name: shape for shape in scene.shapes}
    if curve.shape not in shapes:
        return f"refers to unknown shape '{curve.shape}'"
    if not isinstance(curve, Outline) and curve.side not in shapes[curve.shape].sides:
        return f"shape '{curve.shape}' has no side '{curve.side}'"
    return None


def _expressions(scene: Scene) -> list[Finding]:
    texts = [(f"source '{key}'", key, text) for key, text in scene.source.items()]
    for boundary in scene.boundaries:
        if boundary.condition is not None:
            for key, text in boundary.condition.values.items():
                texts.append((f"boundary '{boundary.name}'", key, text))
    findings = []
    for subject, key, text in texts:
        try:
            parse(text)
        except ExpressionError as error:
            findings.append(_error("expressions", subject, f"{key} = {text!r}: {error}"))
    return findings


def _is_spd(matrix: np.ndarray) -> bool:
    scale = max(1.0, float(np.abs(matrix).max()))
    if not np.allclose(matrix, matrix.T, rtol=0.0, atol=SYMMETRY_TOLERANCE * scale):
        return False
    return bool(np.all(np.linalg.eigvalsh(matrix) > 0.0))


def _material_tensors(scene: Scene) -> list[Finding]:
    findings = []
    for region in scene.regions:
        for key, value in region.material.items():
            if isinstance(value, (int, float)):
                continue
            subject = f"region '{region.name}'"
            matrix = np.array(value, dtype=float)
            if matrix.shape != (2, 2) or not np.all(np.isfinite(matrix)):
                findings.append(_error("material-tensor", subject, f"{key} is not a 2x2 matrix"))
            elif not _is_spd(matrix):
                message = f"{key} is not symmetric positive definite"
                findings.append(_error("material-tensor", subject, message))
    return findings


def _region_materials(scene: Scene) -> list[Finding]:
    return [
        _error("region-material", f"region '{region.name}'", "has no material")
        for region in scene.regions
        if not region.material
    ]


def _boundary_defaults(scene: Scene) -> list[Finding]:
    return [
        _warning(
            "boundary-default",
            f"boundary '{boundary.name}'",
            "has no condition, so it is insulating (neumann, g = 0)",
        )
        for boundary in scene.boundaries
        if boundary.condition is None and not isinstance(boundary.curve, Between)
    ]


def _dirichlet(scene: Scene) -> list[Finding]:
    if any(b.condition is not None and b.condition.kind == "dirichlet" for b in scene.boundaries):
        return []
    message = "no dirichlet boundary, so the solution is defined only up to a constant"
    return [_warning("no-dirichlet", "scene", message)]


def validate(scene: Scene) -> list[Finding]:
    """Every problem found in the scene; an empty list means it can be meshed."""
    rules = (
        _names,
        _shape_parameters,
        _references,
        _expressions,
        _material_tensors,
        _region_materials,
        _boundary_defaults,
        _dirichlet,
    )
    return [finding for rule in rules for finding in rule(scene)]
