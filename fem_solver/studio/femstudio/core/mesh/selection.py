import gmsh
import numpy as np

from femstudio.core.mesh.geometry import CURVE, SURFACE, DimTag
from femstudio.core.scene.boundary import Between, Curve, Outline
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.shapes import Circle, Shape

SAMPLES = 9
TOLERANCE = 1e-6


def _segment_distance(points: np.ndarray, p, q) -> np.ndarray:
    p, q = np.asarray(p, dtype=float), np.asarray(q, dtype=float)
    direction = q - p
    t = np.clip((points - p) @ direction / (direction @ direction), 0.0, 1.0)
    return np.linalg.norm(points - (p + t[:, None] * direction), axis=1)


def _distance_to_curve(points: np.ndarray, shape: Shape, side: str | None) -> np.ndarray:
    if isinstance(shape, Circle):
        return np.abs(np.linalg.norm(points - np.asarray(shape.center), axis=1) - shape.radius)
    corners = shape.points
    segments = [(corners[i], corners[(i + 1) % len(corners)]) for i in range(len(corners))]
    if side is not None:
        segments = [segments[shape.sides.index(side)]]
    return np.min([_segment_distance(points, p, q) for p, q in segments], axis=0)


def _sample(curve: int) -> np.ndarray:
    lower, upper = gmsh.model.getParametrizationBounds(CURVE, curve)
    params = np.linspace(lower[0], upper[0], SAMPLES).tolist()
    return np.array(gmsh.model.getValue(CURVE, curve, params)).reshape(-1, 3)[:, :2]


def midpoint(curve: int) -> tuple[float, float]:
    x, y = _sample(curve)[SAMPLES // 2]
    return float(x), float(y)


def _curve_tags(dimtags: list[DimTag]) -> set[int]:
    return {tag for _, tag in dimtags}


def curves_of(curve: Curve, scene: Scene, regions: dict[str, list[DimTag]]) -> list[int]:
    """Tags of the model curves a boundary names, found by geometry and region adjacency."""
    if isinstance(curve, Between):
        shared = None
        for name in (curve.first, curve.second):
            edges = gmsh.model.getBoundary(regions[name], combined=True, oriented=False)
            shared = _curve_tags(edges) if shared is None else shared & _curve_tags(edges)
        return sorted(shared)
    shape = scene.shape(curve.shape)
    side = None if isinstance(curve, Outline) else curve.side
    return sorted(
        tag
        for _, tag in gmsh.model.getEntities(CURVE)
        if _distance_to_curve(_sample(tag), shape, side).max() < TOLERANCE
    )


def is_in_domain(curve: int, regions: dict[str, list[DimTag]]) -> bool:
    """False for a curve that touches none of the region surfaces."""
    if gmsh.model.getAdjacencies(CURVE, curve)[0].size:
        return True
    x, y = midpoint(curve)
    surfaces = [tag for dimtags in regions.values() for dim, tag in dimtags if dim == SURFACE]
    return any(gmsh.model.isInside(SURFACE, s, [x, y, 0.0]) for s in surfaces)


def exterior_curves(regions: dict[str, list[DimTag]]) -> set[int]:
    """Curves that bound exactly one region surface: the outer edge and the edges of holes."""
    surfaces = [dimtag for dimtags in regions.values() for dimtag in dimtags]
    return _curve_tags(gmsh.model.getBoundary(surfaces, combined=True, oriented=False))


def surfaces_are_connected(regions: dict[str, list[DimTag]]) -> bool:
    """Whether the region surfaces form one piece when joined through shared curves."""
    surfaces = [dimtag for dimtags in regions.values() for dimtag in dimtags]
    parent = {dimtag: dimtag for dimtag in surfaces}

    def root(item):
        while parent[item] != item:
            item = parent[item]
        return item

    by_curve: dict[int, DimTag] = {}
    for dimtag in surfaces:
        for _, curve in gmsh.model.getBoundary([dimtag], combined=False, oriented=False):
            if curve in by_curve:
                parent[root(dimtag)] = root(by_curve[curve])
            by_curve[curve] = dimtag
    return len({root(dimtag) for dimtag in surfaces}) <= 1
