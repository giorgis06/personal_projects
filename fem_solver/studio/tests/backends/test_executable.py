import json
import os
import stat
import time
from pathlib import Path

import numpy as np
import pytest
from examples.capacitor import capacitor_scene
from femstudio.backends.base import BackendUnavailable, SolverError
from femstudio.backends.executable import ENVIRONMENT_VARIABLE, ExecutableBackend
from femstudio.core.mesh.mesher import mesh_scene
from femstudio.core.results.reader import read_solution
from femstudio.physics import registry as physics


@pytest.fixture
def run_folder(tmp_path):
    scene = capacitor_scene()
    mesh = mesh_scene(scene, 0.2, tmp_path / "mesh.msh")
    physics.get("electrostatics").write_problem(scene, mesh, tmp_path)
    return tmp_path, mesh


def test_success_streams_progress_and_returns_the_run_info(fake_fem, run_folder):
    folder, _ = run_folder
    lines = []
    info = ExecutableBackend(fake_fem).solve(folder, lines.append)
    assert lines[0] == "fake fem: problem electrostatics"
    assert lines[-1] == "fake fem: cg iteration 7 residual 1e-11"
    assert (info.status, info.iterations, info.residual) == ("success", 7, 1e-11)
    assert info.timings == {"assemble": 0.01, "solve": 0.02}


def test_result_is_matched_to_the_mesh_by_node_tag(fake_fem, run_folder):
    folder, mesh = run_folder
    ExecutableBackend(fake_fem).solve(folder, lambda line: None)
    field = read_solution(folder / "result", mesh, name="u", unit="V")
    np.testing.assert_allclose(field.values, mesh.nodes[:, 0] + 2.0 * mesh.nodes[:, 1])


def test_row_order_in_the_result_does_not_matter(fake_fem, run_folder, monkeypatch):
    folder, mesh = run_folder
    monkeypatch.setenv("FAKE_FEM_MODE", "shuffled")
    ExecutableBackend(fake_fem).solve(folder, lambda line: None)
    field = read_solution(folder / "result", mesh, name="u", unit="V")
    np.testing.assert_allclose(field.values, mesh.nodes[:, 0] + 2.0 * mesh.nodes[:, 1])


def test_non_zero_exit_carries_the_solvers_message(fake_fem, run_folder, monkeypatch):
    folder, _ = run_folder
    monkeypatch.setenv("FAKE_FEM_MODE", "fail")
    with pytest.raises(SolverError) as caught:
        ExecutableBackend(fake_fem).solve(folder, lambda line: None)
    assert caught.value.message == "matrix is singular: no dirichlet boundary"
    assert caught.value.exit_code == 3


def test_non_zero_exit_without_a_message_still_says_something(fake_fem, run_folder, monkeypatch):
    folder, _ = run_folder
    monkeypatch.setenv("FAKE_FEM_MODE", "silent_fail")
    with pytest.raises(SolverError, match="exited with status 4"):
        ExecutableBackend(fake_fem).solve(folder, lambda line: None)


def test_missing_binary(tmp_path, run_folder):
    folder, _ = run_folder
    backend = ExecutableBackend(tmp_path / "no_such_fem")
    assert not backend.is_available()
    with pytest.raises(BackendUnavailable, match="no_such_fem"):
        backend.solve(folder, lambda line: None)


def test_file_that_cannot_be_executed_is_unavailable(tmp_path):
    plain = tmp_path / "fem"
    plain.write_text("not a program")
    plain.chmod(plain.stat().st_mode & ~(stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    assert not ExecutableBackend(plain).is_available()


def test_available_when_the_file_is_executable(fake_fem):
    assert ExecutableBackend(fake_fem).is_available()


def test_default_path_can_be_set_by_environment(fake_fem, monkeypatch):
    monkeypatch.setenv(ENVIRONMENT_VARIABLE, str(fake_fem))
    assert ExecutableBackend().executable == fake_fem


@pytest.mark.parametrize(
    ("mode", "message"),
    [
        ("malformed_run", "malformed result.*not valid JSON"),
        ("missing_solution", "malformed result.*solution.csv is missing"),
        ("failed_status", "did not converge"),
    ],
)
def test_result_problems_are_solver_errors(fake_fem, run_folder, monkeypatch, mode, message):
    folder, _ = run_folder
    monkeypatch.setenv("FAKE_FEM_MODE", mode)
    with pytest.raises(SolverError, match=message):
        ExecutableBackend(fake_fem).solve(folder, lambda line: None)


def test_a_solver_that_writes_no_result_at_all(tmp_path, run_folder):
    folder, _ = run_folder
    quiet = tmp_path / "quiet_fem"
    quiet.write_text("#!/bin/sh\nexit 0\n")
    quiet.chmod(quiet.stat().st_mode | stat.S_IXUSR)
    with pytest.raises(SolverError, match="malformed result.*run.json is missing"):
        ExecutableBackend(quiet).solve(folder, lambda line: None)


def test_solver_is_run_from_the_run_folder(tmp_path, run_folder):
    folder, _ = run_folder
    probe = tmp_path / "pwd_fem"
    probe.write_text('#!/bin/sh\npwd > "$(dirname "$1")/cwd.txt"\nexit 1\n')
    probe.chmod(probe.stat().st_mode | stat.S_IXUSR)
    with pytest.raises(SolverError):
        ExecutableBackend(probe).solve(folder, lambda line: None)
    assert os.path.samefile((folder / "cwd.txt").read_text().strip(), folder)
    assert json.loads((folder / "problem.json").read_text())["mesh"] == "mesh.msh"


def test_output_that_is_not_utf8_does_not_break_the_stream(fake_fem, run_folder, monkeypatch):
    folder, _ = run_folder
    monkeypatch.setenv("FAKE_FEM_MODE", "binary_output")
    lines = []
    info = ExecutableBackend(fake_fem).solve(folder, lines.append)
    assert info.status == "success"
    assert lines[0].startswith("progress") and "not utf-8" in lines[0]


def test_a_file_that_is_not_a_program_is_a_typed_error(tmp_path, run_folder):
    folder, _ = run_folder
    junk = tmp_path / "fem"
    junk.write_bytes(b"\x00\x01\x02 not an executable")
    junk.chmod(junk.stat().st_mode | stat.S_IXUSR)
    with pytest.raises(BackendUnavailable, match="cannot run"):
        ExecutableBackend(junk).solve(folder, lambda line: None)


def test_relative_executable_and_run_folder(tmp_path, fake_fem, monkeypatch):
    monkeypatch.chdir(tmp_path)
    scene = capacitor_scene()
    mesh = mesh_scene(scene, 0.2, Path("rel_run") / "mesh.msh")
    physics.get("electrostatics").write_problem(scene, mesh, Path("rel_run"))
    relative_exe = Path(os.path.relpath(fake_fem, tmp_path))
    assert not relative_exe.is_absolute()
    info = ExecutableBackend(relative_exe).solve(Path("rel_run"), lambda line: None)
    assert info.status == "success"


def test_an_exception_from_on_log_stops_the_solver(fake_fem, run_folder, monkeypatch):
    folder, _ = run_folder
    monkeypatch.setenv("FAKE_FEM_MODE", "slow")

    def cancel(line):
        raise RuntimeError("cancelled by the user")

    started = time.monotonic()
    with pytest.raises(RuntimeError, match="cancelled by the user"):
        ExecutableBackend(fake_fem).solve(folder, cancel)
    assert time.monotonic() - started < 30
    pid = int((folder / "pid.txt").read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
