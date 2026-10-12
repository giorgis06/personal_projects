import numpy as np

from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.mesh.quality import signed_areas


def gradient(mesh: MeshData, values: np.ndarray) -> np.ndarray:
    """The gradient of a piecewise-linear nodal field, one (dx, dy) per triangle."""
    ia, ib, ic = (mesh.triangles[:, i] for i in range(3))
    (xa, ya), (xb, yb), (xc, yc) = (mesh.nodes[i].T for i in (ia, ib, ic))
    ua, ub, uc = values[ia], values[ib], values[ic]
    with np.errstate(divide="ignore", invalid="ignore"):
        scale = 1.0 / (2.0 * signed_areas(mesh))
    dx = ((yb - yc) * ua + (yc - ya) * ub + (ya - yb) * uc) * scale
    dy = ((xc - xb) * ua + (xa - xc) * ub + (xb - xa) * uc) * scale
    return np.column_stack([dx, dy])


def magnitude(vectors: np.ndarray) -> np.ndarray:
    return np.linalg.norm(vectors, axis=1)


def tensor_per_triangle(mesh: MeshData, by_region: dict) -> np.ndarray:
    """A 2x2 tensor for each triangle from a region name -> number or 2x2 matrix map.

    Triangles in no listed region get nan.
    """
    tensors = np.full((mesh.n_triangles, 2, 2), np.nan)
    for name, value in by_region.items():
        matrix = np.asarray(value, dtype=float)
        tensors[mesh.regions[name]] = matrix * np.eye(2) if matrix.ndim == 0 else matrix
    return tensors


def energy_density(gradients: np.ndarray, tensors: np.ndarray, scale: float = 1.0) -> np.ndarray:
    """scale / 2 * g . (A g) per triangle."""
    return 0.5 * scale * np.einsum("ti,tij,tj->t", gradients, tensors, gradients)
