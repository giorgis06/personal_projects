import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.results.field import Field
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.validation import Finding

FieldKind = Literal["number", "tensor", "expression"]


class ProblemError(ValueError):
    """The scene cannot be turned into a problem; the message names the offender."""


@dataclass(frozen=True)
class FieldSpec:
    """A value a region, boundary kind or source needs. `tensor` is a 2x2 matrix."""

    name: str
    label: str
    kind: FieldKind
    default: float | tuple | str
    unit: str = ""


@dataclass(frozen=True)
class BoundaryKindSpec:
    name: str
    label: str
    fields: tuple[FieldSpec, ...]


@dataclass(frozen=True)
class OutputFieldSpec:
    """A field the solver returns, or one derived from it (`derived`)."""

    name: str
    label: str
    unit: str
    derived: bool
    vector: bool = False


@dataclass(frozen=True)
class SolverSettings:
    method: str = "cg"
    tolerance: float = 1e-10
    max_iterations: int = 10000

    def __post_init__(self) -> None:
        if not (math.isfinite(self.tolerance) and self.tolerance > 0):
            raise ProblemError("solver tolerance must be a finite positive number")
        if not (isinstance(self.max_iterations, int) and self.max_iterations >= 1):
            raise ProblemError("solver max_iterations must be a positive integer")


class ProblemType(ABC):
    """A kind of physics, described as data so forms and checks need not know which."""

    name: str
    label: str
    material_fields: tuple[FieldSpec, ...]
    boundary_kinds: tuple[BoundaryKindSpec, ...]
    source_fields: tuple[FieldSpec, ...]
    output_fields: tuple[OutputFieldSpec, ...]

    def boundary_kind(self, name: str) -> BoundaryKindSpec | None:
        return next((kind for kind in self.boundary_kinds if kind.name == name), None)

    def validate(self, scene: Scene) -> list[Finding]:
        """What the scene's values lack or add compared with this problem type's fields."""
        findings = []
        if scene.problem_type != self.name:
            message = f"is for '{scene.problem_type}', not '{self.name}'"
            findings.append(_error("problem-type", "scene", message))
        for region in scene.regions:
            findings += _check_values(
                f"region '{region.name}'", region.material, self.material_fields, "material-fields"
            )
            findings += self._check_material_types(region.name, region.material)
        findings += _check_unknown("source", scene.source, self.source_fields, "source-fields")
        conditions = [(f"boundary '{b.name}'", b.condition) for b in scene.boundaries]
        conditions.append(("default boundary", scene.default_boundary))
        for subject, condition in conditions:
            if condition is not None:
                findings += self._check_condition(subject, condition)
        return findings

    def _check_material_types(self, region: str, material: dict) -> list[Finding]:
        findings = []
        subject = f"region '{region}'"
        for spec in self.material_fields:
            value = material.get(spec.name)
            if value is None:
                continue
            if isinstance(value, (int, float)):
                if not math.isfinite(value):
                    findings.append(
                        _error("material-fields", subject, f"{spec.name} is not finite")
                    )
                elif spec.kind == "tensor" and value <= 0:
                    message = f"{spec.name} as a single number must be positive"
                    findings.append(_error("material-fields", subject, message))
            elif not (spec.kind == "tensor" and isinstance(value, tuple)):
                wanted = "number or 2x2 matrix" if spec.kind == "tensor" else "number"
                findings.append(
                    _error("material-fields", subject, f"{spec.name} must be a {wanted}")
                )
        return findings

    def _check_condition(self, subject: str, condition) -> list[Finding]:
        kind = self.boundary_kind(condition.kind)
        if kind is None:
            allowed = ", ".join(k.name for k in self.boundary_kinds)
            message = f"kind '{condition.kind}' is not one of: {allowed}"
            return [_error("boundary-kind", subject, message)]
        return _check_values(subject, condition.values, kind.fields, "boundary-fields")

    def derive(self, scene: Scene, mesh: MeshData, solution: Field) -> dict[str, Field]:
        """The derived output fields, by name; none unless a problem type defines some."""
        return {}

    @abstractmethod
    def write_problem(
        self,
        scene: Scene,
        mesh: MeshData,
        folder: Path,
        settings: SolverSettings = SolverSettings(),  # noqa: B008
    ) -> Path:
        """Write `problem.json` into `folder`, next to the mesh file; return its path."""


def _error(rule: str, subject: str, message: str) -> Finding:
    return Finding("error", rule, subject, message)


def _check_unknown(subject, values, fields, rule) -> list[Finding]:
    known = {f.name for f in fields}
    return [_error(rule, subject, f"unknown field '{key}'") for key in values if key not in known]


def _check_values(subject, values, fields, rule) -> list[Finding]:
    findings = _check_unknown(subject, values, fields, rule)
    findings += [
        _error(rule, subject, f"missing field '{spec.name}'")
        for spec in fields
        if spec.name not in values
    ]
    return findings
