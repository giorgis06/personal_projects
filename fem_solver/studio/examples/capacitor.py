"""The cylindrical capacitor. `python -m examples.capacitor` rewrites capacitor.scene.json."""

from pathlib import Path

from femstudio.core.scene.boundary import Boundary, BoundaryCondition
from femstudio.core.scene.region import Region
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.serialization import save_scene
from femstudio.core.scene.shapes import Circle

ELECTRODE_RADIUS = 0.2
GLASS_RADIUS = 0.5
WALL_RADIUS = 2.0


def capacitor_scene() -> Scene:
    electrode = Circle("electrode", (0.0, 0.0), ELECTRODE_RADIUS)
    glass_outer = Circle("glass_outer", (0.0, 0.0), GLASS_RADIUS)
    wall = Circle("wall", (0.0, 0.0), WALL_RADIUS)
    return Scene(
        problem_type="electrostatics",
        shapes=[electrode, glass_outer, wall],
        regions=[
            Region("glass", glass_outer - electrode, {"epsilon": ((4.0, 0.0), (0.0, 4.0))}),
            Region("air", wall - glass_outer, {"epsilon": ((1.0, 0.0), (0.0, 1.0))}),
        ],
        boundaries=[
            Boundary("inner_electrode", "electrode", BoundaryCondition("dirichlet", {"g": "5"})),
            Boundary("outer_wall", "wall", BoundaryCondition("dirichlet", {"g": "0"})),
        ],
        source={"rho": "0"},
    )


if __name__ == "__main__":
    save_scene(capacitor_scene(), Path(__file__).with_name("capacitor.scene.json"))
