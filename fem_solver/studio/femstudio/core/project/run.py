import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.mesh.mesher import mesh_scene
from femstudio.core.mesh.reader import read_mesh
from femstudio.core.results.field import Field
from femstudio.core.results.reader import RunInfo, read_solution
from femstudio.core.scene.scene import Scene

if TYPE_CHECKING:
    from femstudio.backends.base import SolverBackend
    from femstudio.physics.base import ProblemType, SolverSettings

PROBLEM_FILE = "problem.json"
MESH_FILE = "mesh.msh"
RESULT_DIR = "result"
LOG_FILE = "log.txt"
STATUS_FILE = "status.json"


@dataclass
class RunResult:
    mesh: MeshData
    solution: Field
    info: RunInfo


class Run:
    """One solve: a folder with the problem, mesh, result, log and status."""

    def __init__(self, folder: Path) -> None:
        self.folder = Path(folder)

    @property
    def number(self) -> int:
        return int(self.folder.name.removeprefix("run_"))

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
        """created, running, success or failed."""
        return self._status().get("state", "created")

    @property
    def message(self) -> str:
        return self._status().get("message", "")

    def _status(self) -> dict:
        path = self.folder / STATUS_FILE
        return json.loads(path.read_text()) if path.is_file() else {}

    def _set_state(self, state: str, message: str = "") -> None:
        (self.folder / STATUS_FILE).write_text(
            json.dumps({"state": state, "message": message}, indent=2) + "\n"
        )

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
        with self.log_path.open("w") as log:

            def emit(line: str) -> None:
                log.write(line.rstrip("\n") + "\n")
                log.flush()
                if on_log is not None:
                    on_log(line)

            self._set_state("running")
            try:
                mesh = mesh_scene(scene, size, self.mesh_path, emit)
                if settings is None:
                    problem_type.write_problem(scene, mesh, self.folder)
                else:
                    problem_type.write_problem(scene, mesh, self.folder, settings)
                info = backend.solve(self.folder, emit)
                solution = read_solution(self.result_dir, mesh)
            except Exception as error:
                self._set_state("failed", str(error))
                raise
            self._set_state("success", info.message)
        return RunResult(mesh, solution, info)

    def load_result(self) -> RunResult:
        """Read back a finished run from its folder."""
        from femstudio.core.results.reader import read_run_info

        mesh = read_mesh(self.mesh_path)
        return RunResult(mesh, read_solution(self.result_dir, mesh), read_run_info(self.result_dir))
