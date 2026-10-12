import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

import femstudio
from femstudio.ui.session import RunPlan

JOB_MODULE = "femstudio.core.project.run_job"
PACKAGE_PARENT = Path(femstudio.__file__).resolve().parents[1]
KILL_AFTER_MS = 5000


class SolveProcess(QObject):
    """Runs a prepared run folder as a separate Python process and streams its log.

    A solve in its own process keeps gmsh and the solver away from the window's thread, and a
    stop is a SIGTERM that works even when the solver prints nothing.
    """

    logLine = Signal(str)
    ended = Signal(int, str)  # exit status, what the process wrote to stderr

    def __init__(self, plan: RunPlan, backend: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._plan = plan
        self._backend = backend
        self._pending = ""
        self._process = QProcess(self)
        self._process.readyReadStandardOutput.connect(self._read_output)
        self._process.finished.connect(self._finished)
        self._process.errorOccurred.connect(self._error)
        self._failed_to_start = False

    def _command(self) -> list[str]:
        settings = self._plan.settings
        return [
            "-m",
            JOB_MODULE,
            str(self._plan.run.folder),
            "--backend",
            self._backend,
            "--size",
            repr(self._plan.size),
            "--method",
            settings.method,
            "--tolerance",
            repr(settings.tolerance),
            "--max-iterations",
            str(settings.max_iterations),
        ]

    def start(self) -> None:
        environment = QProcessEnvironment.systemEnvironment()
        paths = [str(PACKAGE_PARENT), *filter(None, [os.environ.get("PYTHONPATH")])]
        environment.insert("PYTHONPATH", os.pathsep.join(paths))
        self._process.setProcessEnvironment(environment)
        self._process.start(sys.executable, self._command())

    def running(self) -> bool:
        return self._process.state() != QProcess.ProcessState.NotRunning

    def stop(self) -> None:
        if self.running():
            self._process.terminate()

    def wait(self, milliseconds: int) -> bool:
        """Wait for the process to end, killing it if a stop is not honoured in time."""
        if not self.running():
            return True
        if self._process.waitForFinished(milliseconds):
            return True
        self._process.kill()
        return self._process.waitForFinished(KILL_AFTER_MS)

    def _read_output(self) -> None:
        text = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
        *lines, self._pending = (self._pending + text).split("\n")
        for line in lines:
            self.logLine.emit(line.rstrip("\r"))

    def _finished(self, exit_code: int, _status) -> None:
        self._read_output()
        if self._pending:
            self.logLine.emit(self._pending)
            self._pending = ""
        errors = bytes(self._process.readAllStandardError()).decode("utf-8", errors="replace")
        self.ended.emit(exit_code, errors)

    def _error(self, error) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self.ended.emit(-1, f"cannot start the solve process: {self._process.errorString()}")
