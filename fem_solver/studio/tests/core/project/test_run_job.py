import os
import signal
import subprocess
import sys
import time

import pytest
from examples.capacitor import capacitor_scene
from femstudio.core.project.project import Project
from femstudio.core.scene.serialization import save_scene
from tests.conftest import STUDIO

ARGUMENTS = ["--size", "0.2", "--method", "cg", "--tolerance", "1e-10", "--max-iterations", "100"]


@pytest.fixture
def folder(tmp_path):
    run = Project.create(tmp_path / "project", capacitor_scene()).new_run()
    save_scene(capacitor_scene(), run.scene_path)
    return run.folder


def start(folder, backend, **env):
    command = [sys.executable, "-m", "femstudio.core.project.run_job", str(folder)]
    command += ["--backend", backend, *ARGUMENTS]
    environment = {**os.environ, "PYTHONPATH": str(STUDIO), **env}
    return subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment
    )


def test_a_run_folder_is_solved_and_its_log_goes_to_stdout(folder):
    process = start(folder, "mock")
    out, err = process.communicate(timeout=60)
    assert process.returncode == 0, err
    assert "mock solver: reading mesh" in out
    assert (folder / "result" / "solution.csv").is_file()
    assert '"state": "success"' in (folder / "status.json").read_text()


def test_a_failure_is_a_message_on_stderr_and_a_failed_status(folder, fake_fem):
    process = start(folder, "fem", FEM_EXECUTABLE=str(fake_fem), FAKE_FEM_MODE="fail")
    out, err = process.communicate(timeout=60)
    assert process.returncode == 1
    assert "no dirichlet boundary" in err
    assert '"state": "failed"' in (folder / "status.json").read_text()


def test_an_unknown_backend_fails_without_a_traceback(folder):
    process = start(folder, "nope")
    out, err = process.communicate(timeout=60)
    assert process.returncode == 1
    assert "no backend 'nope'" in err
    assert "Traceback" not in err


def test_sigterm_stops_the_solve_and_the_solver_with_it(folder, fake_fem):
    process = start(folder, "fem", FEM_EXECUTABLE=str(fake_fem), FAKE_FEM_MODE="chatty")
    deadline = time.monotonic() + 30
    while "fake fem: step" not in (process.stdout.readline() or ""):
        assert time.monotonic() < deadline and process.poll() is None
    process.send_signal(signal.SIGTERM)
    _, err = process.communicate(timeout=30)
    assert process.returncode == 1
    assert "stopped by the user" in err
    assert '"state": "failed"' in (folder / "status.json").read_text()
