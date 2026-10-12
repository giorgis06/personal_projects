from collections.abc import Callable
from pathlib import Path

import gmsh

from femstudio.core.mesh import geometry, selection
from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.mesh.reader import read_mesh
from femstudio.core.mesh.session import gmsh_session
from femstudio.core.scene.boundary import DEFAULT_BOUNDARY_NAME, Between, Outline
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.validation import validate


class MeshError(ValueError):
    """The scene cannot be meshed; the message names the offending region or boundary."""


def _build_regions(scene: Scene) -> dict[str, list[geometry.DimTag]]:
    """Add every region and the curves boundaries need, fragment them, return surfaces by region."""
    areas = [geometry.add_area(region.area) for region in scene.regions]
    for region, surfaces in zip(scene.regions, areas, strict=True):
        if not surfaces:
            raise MeshError(f"region '{region.name}' is empty")
    curves = []
    for boundary in scene.boundaries:
        if isinstance(boundary.curve, Between):
            continue
        side = None if isinstance(boundary.curve, Outline) else boundary.curve.side
        curves += geometry.add_outline(scene.shape(boundary.curve.shape), side)

    flat = [dimtag for surfaces in areas for dimtag in surfaces]
    if len(flat) == 1 and not curves:
        mapping = [[flat[0]]]
    else:
        _, mapping = gmsh.model.occ.fragment(flat[:1], flat[1:] + curves)
    gmsh.model.occ.synchronize()

    regions, offset = {}, 0
    for region, surfaces in zip(scene.regions, areas, strict=True):
        pieces = mapping[offset : offset + len(surfaces)]
        offset += len(surfaces)
        regions[region.name] = sorted({dimtag for piece in pieces for dimtag in piece})
    _reject_overlaps(regions)
    return regions


def _reject_overlaps(regions: dict[str, list[geometry.DimTag]]) -> None:
    owner: dict[geometry.DimTag, str] = {}
    for name, dimtags in regions.items():
        for dimtag in dimtags:
            if dimtag in owner:
                raise MeshError(f"regions '{owner[dimtag]}' and '{name}' overlap")
            owner[dimtag] = name


def _name_groups(scene: Scene, regions: dict[str, list[geometry.DimTag]]) -> None:
    """The one place gmsh tag numbers are chosen: 1, 2, ... in scene order."""
    for number, region in enumerate(scene.regions, start=1):
        tags = [tag for _, tag in regions[region.name]]
        gmsh.model.addPhysicalGroup(2, tags, number, region.name)
    if not selection.surfaces_are_connected(regions):
        raise MeshError("the regions do not form one connected piece")

    claimed: dict[int, str] = {}
    for number, boundary in enumerate(scene.boundaries, start=1):
        found = selection.curves_of(boundary.curve, scene, regions)
        if not found:
            raise MeshError(f"boundary '{boundary.name}' matches no curve of the geometry")
        tags = [tag for tag in found if selection.is_in_domain(tag, regions)]
        if not tags:
            raise MeshError(f"boundary '{boundary.name}' lies outside every region")
        for tag in tags:
            if tag in claimed:
                names = f"'{claimed[tag]}' and '{boundary.name}'"
                raise MeshError(f"boundaries {names} both name the same curve")
            claimed[tag] = boundary.name
        gmsh.model.addPhysicalGroup(1, tags, number, boundary.name)
    _name_leftover_edges(scene, regions, set(claimed), len(scene.boundaries) + 1)


def _name_leftover_edges(scene: Scene, regions, named: set[int], number: int) -> None:
    leftover = sorted(selection.exterior_curves(regions) - named)
    if not leftover:
        return
    if scene.default_boundary is None:
        x, y = selection.midpoint(leftover[0])
        raise MeshError(
            f"{len(leftover)} outer curve(s) are named by no boundary, for example near "
            f"({x:.3g}, {y:.3g}); name them or set a default boundary"
        )
    gmsh.model.addPhysicalGroup(1, leftover, number, DEFAULT_BOUNDARY_NAME)


def mesh_scene(
    scene: Scene, size: float, path: Path, on_log: Callable[[str], None] | None = None
) -> MeshData:
    """Mesh the scene with elements no longer than `size`, write `path`, return what was written."""
    problems = [f"{f.subject}: {f.message}" for f in validate(scene) if f.severity == "error"]
    if problems:
        raise MeshError("; ".join(problems))
    if not size > 0:
        raise MeshError("mesh size must be positive")
    if not scene.regions:
        raise MeshError("the scene has no regions")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with gmsh_session(on_log):
            regions = _build_regions(scene)
            _name_groups(scene, regions)
            gmsh.option.setNumber("Mesh.MeshSizeMax", size)
            gmsh.model.mesh.generate(2)
            gmsh.write(str(path))
        return read_mesh(path, on_log)
    except MeshError:
        raise
    except Exception as error:
        raise MeshError(f"gmsh failed: {error}") from error
