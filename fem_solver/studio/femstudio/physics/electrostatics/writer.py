import json
from pathlib import Path

from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.scene.boundary import DEFAULT_BOUNDARY_NAME, Between
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.validation import validate
from femstudio.physics.base import (
    MESH_FILE,
    PROBLEM_FILE,
    RESULT_DIR,
    FieldSpec,
    ProblemError,
    ProblemType,
    SolverSettings,
)

SCHEMA_VERSION = 1
INSULATING = {"kind": "neumann", "g": "0"}


def _matrix(value) -> list[list[float]]:
    if isinstance(value, (int, float)):
        return [[float(value), 0.0], [0.0, float(value)]]
    return [[float(v) for v in row] for row in value]


def _material(spec_fields: tuple[FieldSpec, ...], values: dict) -> dict:
    return {
        spec.name: _matrix(values[spec.name]) if spec.kind == "tensor" else values[spec.name]
        for spec in spec_fields
    }


def _require_names(scene: Scene, mesh: MeshData) -> None:
    for region in scene.regions:
        if region.name not in mesh.regions:
            raise ProblemError(f"region '{region.name}' is not in the mesh")
    for boundary in scene.boundaries:
        if boundary.name not in mesh.boundaries:
            raise ProblemError(f"boundary '{boundary.name}' is not in the mesh")


def _boundaries(scene: Scene, mesh: MeshData) -> dict:
    result = {}
    for boundary in scene.boundaries:
        if boundary.condition is not None:
            result[boundary.name] = {"kind": boundary.condition.kind, **boundary.condition.values}
        elif not isinstance(boundary.curve, Between):
            result[boundary.name] = dict(INSULATING)
    if DEFAULT_BOUNDARY_NAME in mesh.boundaries:
        default = scene.default_boundary
        if default is None:
            raise ProblemError("the mesh has outer edges the scene gives no condition")
        result[DEFAULT_BOUNDARY_NAME] = {"kind": default.kind, **default.values}
    return result


def write_problem(
    problem_type: ProblemType,
    scene: Scene,
    mesh: MeshData,
    folder: Path,
    settings: SolverSettings,
) -> Path:
    """Write `problem.json` as the solver contract describes it."""
    findings = validate(scene) + problem_type.validate(scene)
    problems = [f"{f.subject}: {f.message}" for f in findings if f.severity == "error"]
    if problems:
        raise ProblemError("; ".join(problems))
    folder = Path(folder)
    if not (folder / MESH_FILE).is_file():
        raise ProblemError(f"{MESH_FILE} is not in {folder}")
    _require_names(scene, mesh)

    document = {
        "schema_version": SCHEMA_VERSION,
        "problem_type": problem_type.name,
        "mesh": MESH_FILE,
        "regions": {
            region.name: _material(problem_type.material_fields, region.material)
            for region in scene.regions
        },
        "source": {
            spec.name: scene.source.get(spec.name, spec.default)
            for spec in problem_type.source_fields
        },
        "boundaries": _boundaries(scene, mesh),
        "solver": {
            "method": settings.method,
            "tolerance": settings.tolerance,
            "max_iterations": settings.max_iterations,
        },
        "output": RESULT_DIR,
    }
    path = folder / PROBLEM_FILE
    path.write_text(json.dumps(document, indent=2) + "\n")
    return path
