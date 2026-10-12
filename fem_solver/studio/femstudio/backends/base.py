from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

from femstudio.core.results.reader import RunInfo

ANY_PROBLEM_TYPE = "*"


class SolverError(RuntimeError):
    """The solver failed; `message` is what it said and `exit_code` its exit status, if any."""

    def __init__(self, message: str, exit_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


class BackendUnavailable(SolverError):
    """The backend cannot run here, for example because its executable is missing."""


class SolverBackend(ABC):
    name: str
    supported_problem_types: tuple[str, ...]

    def supports(self, problem_type: str) -> bool:
        types = self.supported_problem_types
        return ANY_PROBLEM_TYPE in types or problem_type in types

    @abstractmethod
    def is_available(self) -> bool:
        """Whether `solve` can run on this machine."""

    @abstractmethod
    def solve(self, run_folder: Path, on_log: Callable[[str], None]) -> RunInfo:
        """Solve the problem in `run_folder`, streaming log lines; return the run's info.

        Raises SolverError, with the solver's message, when the solve does not succeed.
        """
