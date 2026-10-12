from dataclasses import dataclass

import numpy as np


@dataclass
class MeshData:
    """A 2D triangle mesh with its named regions and boundary edges.

    `node_tags` holds each node's gmsh tag, the key used in solver result files.
    `edges` holds every line element; `boundaries` lists the ones each name covers.
    """

    nodes: np.ndarray  # (N, 2) x, y
    node_tags: np.ndarray  # (N,)
    triangles: np.ndarray  # (T, 3) indices into nodes
    edges: np.ndarray  # (E, 2) indices into nodes
    regions: dict[str, np.ndarray]  # name -> triangle indices
    boundaries: dict[str, np.ndarray]  # name -> edge indices

    @property
    def n_nodes(self) -> int:
        return len(self.nodes)

    @property
    def n_triangles(self) -> int:
        return len(self.triangles)
