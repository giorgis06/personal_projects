import json
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.mesh.mesher import mesh_scene
from femstudio.core.mesh.reader import read_mesh
from femstudio.core.results.field import Field
from femstudio.core.results.reader import RunInfo, read_run_info, read_solution
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.serialization import load_scene, save_scene

if TYPE_CHECKING:
    from femstudio.backends.base import SolverBackend
    from femstudio.physics.base import OutputFieldSpec, ProblemType, SolverSettings

SCENE_FILE = "scene.json"
PROBLEM_FILE = "problem.json"
MESH_FILE = "mesh.msh"
RESULT_DIR = "result"
LOG_FILE = "log.txt"
STATUS_FILE = "status.json"

_RUN_NAME = re.compile(r"run_(\d+)")


@dataclass
class RunResult:
    scene: Scene
    mesh: MeshData
    solution: Field
    info: RunInfo


def is_run_folder(folder: Path) -> bool:
    return folder.is_dir() and _RUN_NAME.fullmatch(folder.name) is not None


def _solved_field(problem_type: "ProblemType") -> "OutputFieldSpec":
    solved = [spec for spec in problem_type.output_fields if not spec.derived]
    if len(solved) != 1:
        raise ValueError(f"'{problem_type.name}' must have exactly one solved output field")
    return solved[0]


class Run:
    """One solve: a folder with the scene, problem, mesh, result, log and status."""

    def __init__(self, folder: Path) -> None:
        self.folder = Path(folder).resolve()

    @property
    def number(self) -> int:
        match = _RUN_NAME.fullmatch(self.folder.name)
        if match is None:
            raise ValueError(f"{self.folder.name!r} is not a run folder name")
        return int(match.group(1))

    @property
    def scene_path(self) -> Path:
        return self.folder / SCENE_FILE

    @property
    def problem_path(self) -> Path:
        return self.folder / PROBLEM_FILE

    @property
    def mesh_path(self) -> Path:
        return self.folder / MESH_FILE

    @property
    def result_dir(self) -> Path:
        return self.folder / RESULT_DIR

    @property
    def log_path(self) -> Path:
        return self.folder / LOG_FILE

    @property
    def state(self) -> str:
        """created, running, success or failed; an unreadable status file counts as failed."""
        return self._status().get("state", "created")

    @property
    def message(self) -> str:
        return self._status().get("message", "")

    def _status(self) -> dict:
        path = self.folder / STATUS_FILE
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text())
            return {"state": str(data["state"]), "message": str(data.get("message", ""))}
        except (ValueError, KeyError, TypeError):
            return {"state": "failed", "message": f"{STATUS_FILE} cannot be read"}

    def _set_state(self, state: str, message: str = "") -> None:
        (self.folder / STATUS_FILE).write_text(
            json.dumps({"state": state, "message": message}, indent=2) + "\n"
        )

    def abandon(self, message: str) -> None:
        """Record a run whose process ended unfinished, e.g. stopped before it wrote a status."""
        if self.state in ("created", "running"):
            self._set_state("failed", message)

    def execute(
        self,
        scene: Scene,
        problem_type: "ProblemType",
        backend: "SolverBackend",
        size: float,
        settings: "SolverSettings | None" = None,
        on_log: Callable[[str], None] | None = None,
    ) -> RunResult:
        """Mesh, write the problem, solve, read the result; a failure is recorded, then raised."""
        shutil.rmtree(self.result_dir, ignore_errors=True)
        save_scene(scene, self.scene_path)
        with self.log_path.open("w") as log:

            def emit(line: str) -> None:
                log.write(line.rstrip("\n") + "\n")
                log.flush()
                if on_log is not None:
                    on_log(line)

            self._set_state("running")
            try:
                solved = _solved_field(problem_type)
                mesh = mesh_scene(scene, size, self.mesh_path, emit)
                if settings is None:
                    problem_type.write_problem(scene, mesh, self.folder)
                else:
                    problem_type.write_problem(scene, mesh, self.folder, settings)
                info = backend.solve(self.folder, emit)
                solution = read_solution(self.result_dir, mesh, name=solved.name, unit=solved.unit)
            except BaseException as error:
                self._set_state("failed", str(error) or type(error).__name__)
                raise
            self._set_state("success", info.message)
        return RunResult(scene, mesh, solution, info)

    def load_scene(self) -> Scene:
        """The scene this run was solved with, whatever the project holds now."""
        return load_scene(self.scene_path)

    def load_result(self, problem_type: "ProblemType") -> RunResult:
        """Read back a finished run from its folder."""
        solved = _solved_field(problem_type)
        mesh = read_mesh(self.mesh_path)
        return RunResult(
            self.load_scene(),
            mesh,
            read_solution(self.result_dir, mesh, name=solved.name, unit=solved.unit),
            read_run_info(self.result_dir),
        )
