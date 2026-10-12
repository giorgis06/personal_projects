import os
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path

from femstudio.backends.base import (
    ANY_PROBLEM_TYPE,
    BackendUnavailable,
    SolverBackend,
    SolverError,
)
from femstudio.backends.registry import register
from femstudio.core.project.run import PROBLEM_FILE, RESULT_DIR
from femstudio.core.results.reader import (
    SOLUTION_FILE,
    ResultError,
    RunInfo,
    read_run_info,
)

ENVIRONMENT_VARIABLE = "FEM_EXECUTABLE"
BUILT_EXECUTABLE = Path(__file__).resolve().parents[3] / "fem"


def default_executable() -> Path:
    return Path(os.environ.get(ENVIRONMENT_VARIABLE) or BUILT_EXECUTABLE)


class ExecutableBackend(SolverBackend):
    """Runs `fem <run_folder>/problem.json` and reads `result/` as the solver contract describes."""

    name = "fem"
    supported_problem_types = (ANY_PROBLEM_TYPE,)  # the solver itself refuses what it lacks

    def __init__(self, executable: Path | None = None) -> None:
        self._executable = Path(executable) if executable is not None else None

    @property
    def executable(self) -> Path:
        return self._executable if self._executable is not None else default_executable()

    def is_available(self) -> bool:
        """Whether the file exists and can be run. The contract has no probe to ask more."""
        path = self.executable
        return path.is_file() and os.access(path, os.X_OK)

    def solve(self, run_folder: Path, on_log: Callable[[str], None]) -> RunInfo:
        run_folder = Path(run_folder)
        if not self.is_available():
            raise BackendUnavailable(
                f"solver executable not found or not runnable: {self.executable}"
            )
        process = subprocess.Popen(
            [str(self.executable), str(run_folder / PROBLEM_FILE)],
            cwd=run_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        errors: list[str] = []
        reader = threading.Thread(target=lambda: errors.extend(process.stderr), daemon=True)
        reader.start()
        for line in process.stdout:
            on_log(line.rstrip("\n"))
        code = process.wait()
        reader.join()
        if code != 0:
            message = "".join(errors).strip() or f"solver exited with status {code}"
            raise SolverError(message, exit_code=code)
        return self._read_result(run_folder / RESULT_DIR)

    @staticmethod
    def _read_result(result_dir: Path) -> RunInfo:
        try:
            info = read_run_info(result_dir)
        except ResultError as error:
            raise SolverError(f"malformed result: {error}") from error
        if info.status != "success":
            raise SolverError(info.message or f"solver reported status '{info.status}'")
        if not (result_dir / SOLUTION_FILE).is_file():
            raise SolverError(f"malformed result: {SOLUTION_FILE} is missing from {result_dir}")
        return info


register(ExecutableBackend())
