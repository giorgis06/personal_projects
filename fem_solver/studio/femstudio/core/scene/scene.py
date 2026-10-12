from dataclasses import dataclass, field

from femstudio.core.scene.boundary import Boundary, BoundaryCondition
from femstudio.core.scene.region import Region
from femstudio.core.scene.shapes import Shape


@dataclass
class Scene:
    """Geometry and physics, linked by name only.

    `source` maps field names to expressions. `default_boundary` applies to every outer edge no
    boundary names, for example a dirichlet g = 0 for fields that decay at infinity; without
    it, meshing refuses a scene that leaves an outer edge unnamed.
    """

    problem_type: str
    shapes: list[Shape] = field(default_factory=list)
    regions: list[Region] = field(default_factory=list)
    boundaries: list[Boundary] = field(default_factory=list)
    source: dict[str, str] = field(default_factory=dict)
    default_boundary: BoundaryCondition | None = None

    def shape(self, name: str) -> Shape:
        return _find(self.shapes, name, "shape")

    def region(self, name: str) -> Region:
        return _find(self.regions, name, "region")

    def boundary(self, name: str) -> Boundary:
        return _find(self.boundaries, name, "boundary")


def _find(items, name: str, what: str):
    for item in items:
        if item.name == name:
            return item
    raise KeyError(f"no {what} named {name!r}")
