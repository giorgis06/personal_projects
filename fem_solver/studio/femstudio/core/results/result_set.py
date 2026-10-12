from dataclasses import dataclass

import numpy as np

from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.mesh.quality import signed_areas
from femstudio.core.results.field import Field
from femstudio.core.results.probe import locate


@dataclass(frozen=True)
class Reading:
    """A field's value at a point: the number shown, and the components when it is a vector."""

    x: float
    y: float
    triangle: int
    value: float
    components: tuple[float, float] | None = None


@dataclass
class ResultSet:
    """The fields of one run on its mesh: the solved one and the ones derived from it.

    Fields are in display order. A vector field is shown by its magnitude.
    """

    run_number: int
    mesh: MeshData
    fields: dict[str, Field]
    labels: dict[str, str]

    def names(self) -> list[str]:
        return list(self.fields)

    def label(self, name: str) -> str:
        return self.labels.get(name, name)

    def unit(self, name: str) -> str:
        return self.fields[name].unit

    def scalars(self, name: str) -> np.ndarray:
        """One number per node or per triangle (see `location`): the magnitude of a vector."""
        values = self.fields[name].values
        return np.linalg.norm(values, axis=1) if values.ndim == 2 else values

    def location(self, name: str) -> str:
        return self.fields[name].location

    def node_values(self, name: str) -> np.ndarray:
        """The field at every node; a per-triangle field is averaged over a node's triangles."""
        values = self.scalars(name)
        if self.location(name) == "node":
            return values
        areas = np.abs(signed_areas(self.mesh))
        total = np.zeros(self.mesh.n_nodes)
        weight = np.zeros(self.mesh.n_nodes)
        for corner in range(3):
            np.add.at(total, self.mesh.triangles[:, corner], areas * values)
            np.add.at(weight, self.mesh.triangles[:, corner], areas)
        with np.errstate(divide="ignore", invalid="ignore"):
            return total / weight

    def value_range(self, name: str) -> tuple[float, float]:
        """Smallest and largest finite value; (0, 0) when there is none."""
        values = self.scalars(name)
        values = values[np.isfinite(values)]
        if values.size == 0:
            return 0.0, 0.0
        return float(values.min()), float(values.max())

    def reading(self, name: str, x: float, y: float) -> Reading | None:
        """The field at (x, y), or None outside the mesh.

        A nodal field is interpolated linearly inside the triangle; a per-triangle one is the
        triangle's value.
        """
        found = locate(self.mesh, x, y)
        if found is None:
            return None
        triangle, weights = found
        field = self.fields[name]
        if field.location == "node":
            corners = self.mesh.triangles[triangle]
            picked = weights @ field.values[corners]
        else:
            picked = field.values[triangle]
        if field.is_vector:
            components = (float(picked[0]), float(picked[1]))
            return Reading(x, y, triangle, float(np.hypot(*components)), components)
        return Reading(x, y, triangle, float(picked))
