from dataclasses import dataclass

import numpy as np

from femstudio.core.mesh.mesh_data import MeshData


@dataclass(frozen=True)
class QualityStats:
    n_nodes: int
    n_triangles: int
    total_area: float
    min_area: float
    min_angle: float  # degrees
    max_edge: float
    n_inverted: int  # triangles that are not counter-clockwise


def signed_areas(mesh: MeshData) -> np.ndarray:
    """Positive for counter-clockwise triangles."""
    a, b, c = (mesh.nodes[mesh.triangles[:, i]] for i in range(3))
    u, v = b - a, c - a
    return 0.5 * (u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0])


def _min_angles(mesh: MeshData) -> np.ndarray:
    corners = [mesh.nodes[mesh.triangles[:, i]] for i in range(3)]
    angles = []
    for i in range(3):
        u = corners[(i + 1) % 3] - corners[i]
        v = corners[(i + 2) % 3] - corners[i]
        cosine = (u * v).sum(axis=1) / (np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1))
        angles.append(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))
    return np.min(angles, axis=0)


def _max_edge(mesh: MeshData) -> float:
    corners = [mesh.nodes[mesh.triangles[:, i]] for i in range(3)]
    return max(
        float(np.linalg.norm(corners[i] - corners[(i + 1) % 3], axis=1).max()) for i in range(3)
    )


def quality(mesh: MeshData) -> QualityStats:
    areas = signed_areas(mesh)
    return QualityStats(
        n_nodes=mesh.n_nodes,
        n_triangles=mesh.n_triangles,
        total_area=float(np.abs(areas).sum()),
        min_area=float(np.abs(areas).min()),
        min_angle=float(_min_angles(mesh).min()),
        max_edge=_max_edge(mesh),
        n_inverted=int((areas <= 0.0).sum()),
    )
