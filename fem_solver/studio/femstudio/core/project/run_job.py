"""Solve one prepared run folder: `python -m femstudio.core.project.run_job <folder> ...`.

The window starts this as a process, so a solve shares neither gmsh nor the interpreter with it.
Log lines go to stdout; a failure is a message on stderr and exit status 1. SIGTERM stops it,
and the backend then stops the solver.
"""

import argparse
import signal
import sys
from pathlib import Path

from femstudio.backends import registry as backends
from femstudio.backends.base import SolverBackend
from femstudio.core.project.run import Run
from femstudio.physics import registry as physics
from femstudio.physics.base import SolverSettings

STOPPED = "stopped by the user"


class Stopped(Exception):
    pass


def _raise_stopped(_signal, _frame) -> None:
    raise Stopped(STOPPED)


class _StoppableBackend(SolverBackend):
    """Another backend, solving with SIGTERM handled: gmsh resets it to the default when it runs."""

    def __init__(self, backend: SolverBackend) -> None:
        self._backend = backend
        self.name = backend.name
        self.supported_problem_types = backend.supported_problem_types

    def is_available(self) -> bool:
        return self._backend.is_available()

    def solve(self, run_folder, on_log):
        signal.signal(signal.SIGTERM, _raise_stopped)
        return self._backend.solve(run_folder, on_log)


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="run_job", description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--size", type=float, required=True)
    parser.add_argument("--method", required=True)
    parser.add_argument("--tolerance", type=float, required=True)
    parser.add_argument("--max-iterations", type=int, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    arguments = _arguments(argv)
    run = Run(arguments.folder)
    try:
        scene = run.load_scene()
        settings = SolverSettings(arguments.method, arguments.tolerance, arguments.max_iterations)
        run.execute(
            scene,
            physics.get(scene.problem_type),
            _StoppableBackend(backends.get(arguments.backend)),
            arguments.size,
            settings,
            on_log=lambda line: print(line, flush=True),
        )
    except Exception as error:  # noqa: BLE001 - every failure ends as a message and a status
        print(str(error) or type(error).__name__, file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
