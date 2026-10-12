from collections.abc import Callable
from pathlib import Path

import gmsh
import numpy as np

from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.mesh.session import gmsh_session

ELEMENT_TYPE = {2: 2, 1: 1}  # dimension -> gmsh type of a 3-node triangle, 2-node line
NODES_PER_ELEMENT = {2: 3, 1: 2}


class MeshReadError(ValueError):
    """The file cannot be read as a triangle mesh."""


def read_mesh(path: Path, on_log: Callable[[str], None] | None = None) -> MeshData:
    """Read a `.msh`, or mesh a `.geo` at its own sizes. Unnamed physical groups are skipped."""
    path = Path(path)
    if path.suffix not in (".msh", ".geo"):
        raise MeshReadError(f"unsupported file type {path.suffix!r}")
    if not path.is_file():
        raise MeshReadError(f"no such file: {path}")
    try:
        with gmsh_session(on_log):
            gmsh.open(str(path))
            if path.suffix == ".geo":
                gmsh.model.mesh.generate(2)
            return _extract()
    except MeshReadError:
        raise
    except Exception as error:
        raise MeshReadError(f"gmsh could not read {path.name}: {error}") from error


def _elements(dim: int, entity: int):
    types, tags, nodes = gmsh.model.mesh.getElements(dim, entity)
    if any(t != ELEMENT_TYPE[dim] for t in types):
        raise MeshReadError("only first-order triangles and lines are supported")
    width = NODES_PER_ELEMENT[dim]
    if not tags:
        return np.empty(0, dtype=np.int64), np.empty((0, width), dtype=np.int64)
    return (
        np.concatenate(tags).astype(np.int64),
        np.concatenate(nodes).astype(np.int64).reshape(-1, width),
    )


def _group_elements(dim: int, order: np.ndarray, sorted_tags: np.ndarray) -> dict[str, np.ndarray]:
    groups: dict[str, np.ndarray] = {}
    for group_dim, tag in gmsh.model.getPhysicalGroups(dim):
        name = gmsh.model.getPhysicalName(group_dim, tag)
        if not name:
            continue
        found = []
        for entity in gmsh.model.getEntitiesForPhysicalGroup(group_dim, tag):
            element_tags, _ = _elements(dim, entity)
            found.append(order[np.searchsorted(sorted_tags, element_tags)])
        indices = np.concatenate(found) if found else np.empty(0, dtype=np.int64)
        groups[name] = np.union1d(groups.get(name, indices[:0]), indices)
    return groups


def _extract() -> MeshData:
    node_tags, coords, _ = gmsh.model.mesh.getNodes()
    node_tags = np.asarray(node_tags, dtype=np.int64)
    coords = np.asarray(coords).reshape(-1, 3)[:, :2]

    triangle_tags, triangle_nodes = _elements(2, -1)
    edge_tags, edge_nodes = _elements(1, -1)

    triangle_order = np.argsort(triangle_tags)
    edge_order = np.argsort(edge_tags)
    regions = _group_elements(2, triangle_order, triangle_tags[triangle_order])
    boundaries = _group_elements(1, edge_order, edge_tags[edge_order])

    used = np.unique(np.concatenate([triangle_nodes.ravel(), edge_nodes.ravel()]))
    if used.size == 0:
        raise MeshReadError("the mesh has no triangles")
    keep = np.searchsorted(np.sort(node_tags), used)
    sorted_tags = np.sort(node_tags)[keep]
    nodes = coords[np.argsort(node_tags)][keep]
    return MeshData(
        nodes=nodes,
        node_tags=sorted_tags,
        triangles=np.searchsorted(used, triangle_nodes),
        edges=np.searchsorted(used, edge_nodes),
        regions=regions,
        boundaries=boundaries,
    )
