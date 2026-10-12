import csv
import json
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np

from femstudio.backends.base import ANY_PROBLEM_TYPE, SolverBackend, SolverError
from femstudio.backends.registry import register
from femstudio.core.mesh.reader import MeshReadError, read_mesh
from femstudio.core.project.run import MESH_FILE, PROBLEM_FILE, RESULT_DIR
from femstudio.core.results.reader import RUN_FILE, SOLUTION_FILE, SOLUTION_HEADER, RunInfo


def mock_field(nodes: np.ndarray) -> np.ndarray:
    """A cosine bump: 1 at the middle of the nodes' bounding box, 0 on its edges."""
    low, high = nodes.min(axis=0), nodes.max(axis=0)
    centre, size = (low + high) / 2, np.maximum(high - low, np.finfo(float).tiny)
    shifted = np.pi * (nodes - centre) / size
    return np.cos(shifted[:, 0]) * np.cos(shifted[:, 1])


class MockBackend(SolverBackend):
    """Reads the same files as the real solver and writes the same result, but invents the field."""

    name = "mock"
    supported_problem_types = (ANY_PROBLEM_TYPE,)

    def is_available(self) -> bool:
        return True

    def solve(self, run_folder: Path, on_log: Callable[[str], None]):
        run_folder = Path(run_folder)
        if not (run_folder / PROBLEM_FILE).is_file():
            raise SolverError(f"{PROBLEM_FILE} is not in {run_folder}")
        on_log("mock solver: reading mesh")
        started = time.perf_counter()
        try:
            mesh = read_mesh(run_folder / MESH_FILE)
        except MeshReadError as error:
            raise SolverError(str(error)) from error
        values = mock_field(mesh.nodes)
        result = run_folder / RESULT_DIR
        result.mkdir(exist_ok=True)
        with (result / SOLUTION_FILE).open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(SOLUTION_HEADER)
            writer.writerows(zip(mesh.node_tags.tolist(), values.tolist(), strict=True))
        elapsed = time.perf_counter() - started
        message = "mock field, not a solution"
        (result / RUN_FILE).write_text(
            json.dumps(
                {
                    "status": "success",
                    "iterations": 0,
                    "residual": 0.0,
                    "timings": {"total": elapsed},
                    "message": message,
                },
                indent=2,
            )
            + "\n"
        )
        on_log(f"mock solver: wrote {len(values)} values")
        return RunInfo("success", 0, 0.0, {"total": elapsed}, message)


register(MockBackend())
