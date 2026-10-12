import numpy as np

from femstudio.core.mesh.mesh_data import MeshData

INSIDE = 1e-9  # how far outside a triangle's edge a point may lie, in barycentric weight


def locate(mesh: MeshData, x: float, y: float) -> tuple[int, np.ndarray] | None:
    """The triangle holding the point and the point's barycentric weights in it, or None."""
    if mesh.n_triangles == 0:
        return None
    a, b, c = (mesh.nodes[mesh.triangles[:, i]] for i in range(3))
    v0, v1 = b - a, c - a
    v2 = np.array([x, y]) - a
    determinant = v0[:, 0] * v1[:, 1] - v0[:, 1] * v1[:, 0]
    with np.errstate(divide="ignore", invalid="ignore"):
        wb = (v2[:, 0] * v1[:, 1] - v2[:, 1] * v1[:, 0]) / determinant
        wc = (v0[:, 0] * v2[:, 1] - v0[:, 1] * v2[:, 0]) / determinant
    weights = np.column_stack([1.0 - wb - wc, wb, wc])
    inside = np.all(weights >= -INSIDE, axis=1)  # a degenerate triangle gives nan: never inside
    if not inside.any():
        return None
    # A point on a shared edge is inside several triangles; the one it sits deepest in wins.
    depth = np.where(inside, weights.min(axis=1), -np.inf)
    index = int(np.argmax(depth))
    return index, weights[index]
