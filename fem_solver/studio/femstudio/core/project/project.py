from pathlib import Path

from femstudio.core.project.run import Run
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.serialization import load_scene, save_scene

SCENE_FILE = "scene.json"
RUNS_DIR = "runs"


class ProjectError(ValueError):
    pass


class Project:
    """A folder holding one scene and the runs made from it."""

    def __init__(self, folder: Path) -> None:
        self.folder = Path(folder)

    @classmethod
    def create(cls, folder: Path, scene: Scene) -> "Project":
        folder = Path(folder)
        if (folder / SCENE_FILE).exists():
            raise ProjectError(f"{folder} already holds a project")
        folder.mkdir(parents=True, exist_ok=True)
        save_scene(scene, folder / SCENE_FILE)
        return cls(folder)

    @classmethod
    def open(cls, folder: Path) -> "Project":
        if not (Path(folder) / SCENE_FILE).is_file():
            raise ProjectError(f"{folder} holds no {SCENE_FILE}")
        return cls(folder)

    def load_scene(self) -> Scene:
        return load_scene(self.folder / SCENE_FILE)

    def save_scene(self, scene: Scene) -> None:
        save_scene(scene, self.folder / SCENE_FILE)

    def runs(self) -> list[Run]:
        root = self.folder / RUNS_DIR
        found = [Run(p) for p in root.glob("run_*") if p.is_dir()] if root.is_dir() else []
        return sorted(found, key=lambda run: run.number)

    def new_run(self) -> Run:
        """The next numbered, empty run folder."""
        runs = self.runs()
        number = runs[-1].number + 1 if runs else 1
        folder = self.folder / RUNS_DIR / f"run_{number:03d}"
        folder.mkdir(parents=True)
        return Run(folder)

    def run(self, number: int) -> Run:
        folder = self.folder / RUNS_DIR / f"run_{number:03d}"
        if not folder.is_dir():
            raise ProjectError(f"no run {number} in {self.folder}")
        return Run(folder)
