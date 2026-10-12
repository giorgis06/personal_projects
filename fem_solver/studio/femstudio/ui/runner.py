from PySide6.QtCore import QObject, Signal

from femstudio.backends.base import SolverBackend
from femstudio.core.project.document import Document
from femstudio.core.project.run_job import STOPPED
from femstudio.core.scene.validation import Finding
from femstudio.ui.session import RunPlan
from femstudio.ui.workers.solve_worker import SolveProcess

WAIT_FOR_STOP_MS = 15000


def why_not_runnable(
    document: Document | None, findings: list[Finding], backend: SolverBackend | None
) -> str | None:
    """The reason a solve cannot start now, or None when it can."""
    if document is None or document.scene is None:
        return "Open or create a scene first."
    errors = [f for f in findings if f.severity == "error"]
    if errors:
        more = f" (and {len(errors) - 1} more)" if len(errors) > 1 else ""
        return f"{errors[0].subject}: {errors[0].message}{more}"
    if document.mesh is None:
        return f"The scene has no mesh: {document.mesh_error}"
    if backend is None:
        return "No solver backend is chosen."
    if not backend.is_available():
        return f"The '{backend.name}' backend is not available on this machine."
    if not backend.supports(document.scene.problem_type):
        return f"The '{backend.name}' backend does not solve {document.scene.problem_type}."
    return None


class Runner(QObject):
    """One solve at a time, in its own process."""

    started = Signal(int)  # the run number
    finished = Signal(int, str, str)  # run number, "success", "failed" or "stopped", a message
    logLine = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._process: SolveProcess | None = None
        self._plan: RunPlan | None = None
        self._stopping = False

    @property
    def busy(self) -> bool:
        return self._process is not None

    def start(self, plan: RunPlan, backend: SolverBackend) -> None:
        if self._process is not None:
            raise RuntimeError("a solve is already running")
        self._plan = plan
        self._stopping = False
        process = SolveProcess(plan, backend.name, self)
        process.logLine.connect(self.logLine)
        process.ended.connect(self._ended)
        self._process = process
        self.started.emit(plan.run.number)
        process.start()

    def stop(self) -> None:
        if self._process is not None:
            self._stopping = True
            self._process.stop()

    def wait(self) -> bool:
        """Block until the solve has ended, killing it if it ignores a stop; whether it ended."""
        process = self._process
        return process is None or process.wait(WAIT_FOR_STOP_MS)

    def _ended(self, exit_code: int, errors: str) -> None:
        process, self._process = self._process, None
        if process is not None:
            process.deleteLater()
        run = self._plan.run
        if self._stopping:
            state, message = "stopped", STOPPED
        elif exit_code == 0:
            state, message = "success", run.message
        else:
            lines = [line for line in errors.strip().splitlines() if line.strip()]
            state, message = "failed", run.message or (lines[-1] if lines else f"exit {exit_code}")
        if state != "success":
            run.abandon(message)  # a process ended early leaves its status as it was
        self.finished.emit(run.number, state, message)
