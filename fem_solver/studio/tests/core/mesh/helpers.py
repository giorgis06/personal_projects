import numpy as np
from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.scene.boundary import Boundary, BoundaryCondition, Curve
from femstudio.core.scene.region import Region
from femstudio.core.scene.scene import Scene

UNIT = {"epsilon": 1.0}
ZERO = BoundaryCondition("dirichlet", {"g": "0"})


def scene(shapes, regions, boundaries=(), default=None) -> Scene:
    return Scene("electrostatics", list(shapes), list(regions), list(boundaries), {}, default)


def region(name, area) -> Region:
    return Region(name, area, dict(UNIT))


def boundary(name, curve: Curve) -> Boundary:
    return Boundary(name, curve, ZERO)


def region_area(mesh: MeshData, name: str) -> float:
    a, b, c = (mesh.nodes[mesh.triangles[mesh.regions[name], i]] for i in range(3))
    u, v = b - a, c - a
    return float(np.abs(0.5 * (u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0])).sum())


def edge_nodes(mesh: MeshData, name: str) -> np.ndarray:
    return mesh.nodes[np.unique(mesh.edges[mesh.boundaries[name]])]


def edge_length(mesh: MeshData, name: str) -> float:
    ends = mesh.nodes[mesh.edges[mesh.boundaries[name]]]
    return float(np.linalg.norm(ends[:, 0] - ends[:, 1], axis=1).sum())
