from pathlib import Path

from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.scene.scene import Scene
from femstudio.physics.base import (
    BoundaryKindSpec,
    FieldSpec,
    OutputFieldSpec,
    ProblemType,
    SolverSettings,
)
from femstudio.physics.electrostatics.writer import write_problem

EPSILON = FieldSpec("epsilon", "Permittivity", "tensor", ((1.0, 0.0), (0.0, 1.0)))
RHO = FieldSpec("rho", "Charge density", "expression", "0")
G = FieldSpec("g", "Value", "expression", "0", unit="V")
FLUX = FieldSpec("g", "Flux", "expression", "0")
KAPPA = FieldSpec("kappa", "Robin coefficient", "expression", "1")


class Electrostatics(ProblemType):
    name = "electrostatics"
    label = "Electrostatics"
    material_fields = (EPSILON,)
    boundary_kinds = (
        BoundaryKindSpec("dirichlet", "Fixed potential", (G,)),
        BoundaryKindSpec("neumann", "Fixed flux", (FLUX,)),
        BoundaryKindSpec("robin", "Robin", (G, KAPPA)),
    )
    source_fields = (RHO,)
    output_fields = (
        OutputFieldSpec("u", "Potential", "V", derived=False),
        OutputFieldSpec("E", "Electric field", "V/m", derived=True, vector=True),
        OutputFieldSpec("E_magnitude", "Field magnitude", "V/m", derived=True),
        OutputFieldSpec("energy_density", "Energy density", "J/m^3", derived=True),
    )

    def write_problem(
        self,
        scene: Scene,
        mesh: MeshData,
        folder: Path,
        settings: SolverSettings = SolverSettings(),  # noqa: B008
    ) -> Path:
        return write_problem(self, scene, mesh, folder, settings)
