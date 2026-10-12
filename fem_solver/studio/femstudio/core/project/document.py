from dataclasses import dataclass
from pathlib import Path

from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.mesh.mesher import mesh_scene
from femstudio.core.mesh.reader import read_mesh
from femstudio.core.project.project import SCENE_FILE, Project
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.serialization import load_scene

CELLS_ACROSS = 40


class DocumentError(ValueError):
    """The path is not something the studio opens."""


@dataclass
class Document:
    """What is open: a mesh, with the scene and project it came from when there are any."""

    source: Path
    mesh: MeshData
    scene: Scene | None = None
    project: Project | None = None
    size: float | None = None  # element size the scene was meshed with

    @property
    def region_names(self) -> list[str]:
        if self.scene is not None:
            return [region.name for region in self.scene.regions]
        return list(self.mesh.regions)

    @property
    def boundary_names(self) -> list[str]:
        if self.scene is not None:
            return [boundary.name for boundary in self.scene.boundaries]
        return list(self.mesh.boundaries)


def default_mesh_size(scene: Scene) -> float:
    """An element size that puts about 40 elements across the scene's longest side."""
    corners = [corner for shape in scene.shapes for corner in shape.bounds]
    if not corners:
        raise DocumentError("the scene has no shapes to mesh")
    xs, ys = [c[0] for c in corners], [c[1] for c in corners]
    return max(max(xs) - min(xs), max(ys) - min(ys)) / CELLS_ACROSS


def _from_scene(scene: Scene, source: Path, workdir: Path, project: Project | None, on_log):
    size = default_mesh_size(scene)
    mesh = mesh_scene(scene, size, workdir / "mesh.msh", on_log)
    return Document(source, mesh, scene, project, size)


def open_document(path: Path, workdir: Path, on_log=None) -> Document:
    """Open a project folder, a `scene.json`, or a `.msh` / `.geo` mesh.

    Scenes are meshed into `workdir` at a default element size.
    """
    path = Path(path)
    if path.is_dir():
        project = Project.open(path)
        return _from_scene(project.load_scene(), path, workdir, project, on_log)
    if path.suffix == ".json":
        return _from_scene(load_scene(path), path, workdir, None, on_log)
    if path.suffix in (".msh", ".geo"):
        return Document(path, read_mesh(path, on_log))
    raise DocumentError(
        f"cannot open '{path.name}': expected a project folder, {SCENE_FILE}, .msh or .geo"
    )
