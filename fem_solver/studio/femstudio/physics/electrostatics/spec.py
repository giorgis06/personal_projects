import math
from pathlib import Path

from femstudio.core.expressions.evaluate import constant_value
from femstudio.core.expressions.grammar import ExpressionError
from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.validation import Finding
from femstudio.physics.base import (
    BoundaryKindSpec,
    FieldSpec,
    OutputFieldSpec,
    ProblemType,
    SolverSettings,
)
from femstudio.physics.electrostatics.writer import write_problem

EPSILON = FieldSpec("epsilon", "Relative permittivity", "tensor", ((1.0, 0.0), (0.0, 1.0)))
RHO = FieldSpec("rho", "Charge density", "expression", "0", unit="C/m^3")
POTENTIAL = FieldSpec("g", "Potential", "expression", "0", unit="V")
SURFACE_CHARGE = FieldSpec("g", "Surface charge", "expression", "0", unit="C/m^2")
KAPPA = FieldSpec("kappa", "Coupling", "expression", "1", unit="1/m")
U_REF = FieldSpec("u_ref", "Reference potential", "expression", "0", unit="V")


class Electrostatics(ProblemType):
    name = "electrostatics"
    label = "Electrostatics"
    material_fields = (EPSILON,)
    boundary_kinds = (
        BoundaryKindSpec("dirichlet", "Fixed potential", (POTENTIAL,)),
        BoundaryKindSpec("neumann", "Surface charge", (SURFACE_CHARGE,)),
        BoundaryKindSpec("robin", "Coupled to a reference potential", (KAPPA, U_REF)),
    )
    source_fields = (RHO,)
    output_fields = (
        OutputFieldSpec("u", "Potential", "V", derived=False),
        OutputFieldSpec("E", "Electric field", "V/m", derived=True, vector=True),
        OutputFieldSpec("E_magnitude", "Field magnitude", "V/m", derived=True),
        OutputFieldSpec("energy_density", "Energy density", "J/m^3", derived=True),
    )

    def validate(self, scene: Scene) -> list[Finding]:
        findings = super().validate(scene)
        conditions = [(f"boundary '{b.name}'", b.condition) for b in scene.boundaries]
        conditions.append(("default boundary", scene.default_boundary))
        for subject, condition in conditions:
            if condition is not None and condition.kind == "robin":
                findings += _check_kappa(subject, condition.values.get("kappa"))
        return findings

    def write_problem(
        self,
        scene: Scene,
        mesh: MeshData,
        folder: Path,
        settings: SolverSettings = SolverSettings(),  # noqa: B008
    ) -> Path:
        return write_problem(self, scene, mesh, folder, settings)


def _check_kappa(subject: str, text) -> list[Finding]:
    if not isinstance(text, str):
        return []
    try:
        value = constant_value(text)
    except ExpressionError:
        return []
    if value is not None and not (math.isfinite(value) and value > 0):
        return [Finding("error", "boundary-fields", subject, "kappa must be finite and positive")]
    return []
