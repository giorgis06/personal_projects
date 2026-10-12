import json

import numpy as np
import pytest
from examples.capacitor import capacitor_scene
from femstudio.backends import registry as backends
from femstudio.backends.base import SolverBackend, SolverError
from femstudio.core.mesh.mesher import MeshError
from femstudio.core.project.project import Project
from femstudio.core.scene.region import Region
from femstudio.core.scene.shapes import Circle
from femstudio.physics import registry as physics
from femstudio.physics.base import SolverSettings


class Failing(SolverBackend):
    name = "failing"
    supported_problem_types = ("*",)

    def is_available(self):
        return True

    def solve(self, run_folder, on_log):
        on_log("failing solver: starting")
        raise SolverError("diverged after 3 iterations", exit_code=2)


@pytest.fixture
def project(tmp_path):
    return Project.create(tmp_path / "proj", capacitor_scene())


def execute(run, scene, backend="mock", **kwargs):
    return run.execute(
        scene, physics.get("electrostatics"), backends.get(backend), size=0.2, **kwargs
    )


def test_a_run_with_the_mock_backend_produces_a_field_end_to_end(project):
    run = project.new_run()
    lines = []
    result = execute(run, project.load_scene(), on_log=lines.append)
    for name in ("problem.json", "mesh.msh", "log.txt", "status.json"):
        assert (run.folder / name).is_file()
    for name in ("solution.csv", "run.json"):
        assert (run.result_dir / name).is_file()
    assert run.state == "success"
    assert result.solution.values.shape == (result.mesh.n_nodes,)
    assert 0.0 <= result.solution.values.min() and result.solution.values.max() <= 1.0
    assert result.info.status == "success"
    assert any(line.startswith("mock solver") for line in lines)


def test_log_file_holds_what_on_log_received(project):
    run = project.new_run()
    lines = []
    execute(run, project.load_scene(), on_log=lines.append)
    assert run.log_path.read_text().splitlines() == [line.rstrip("\n") for line in lines]
    assert lines


def test_a_finished_run_can_be_loaded_again(project):
    run = project.new_run()
    result = execute(run, project.load_scene())
    loaded = project.run(run.number).load_result()
    np.testing.assert_array_equal(loaded.solution.values, result.solution.values)
    np.testing.assert_array_equal(loaded.mesh.nodes, result.mesh.nodes)
    assert loaded.info == result.info


def test_settings_reach_the_problem_file(project):
    run = project.new_run()
    execute(run, project.load_scene(), settings=SolverSettings(tolerance=1e-6, max_iterations=77))
    solver = json.loads(run.problem_path.read_text())["solver"]
    assert (solver["tolerance"], solver["max_iterations"]) == (1e-6, 77)


def test_solver_failure_is_recorded_and_raised(project, monkeypatch):
    monkeypatch.setattr(backends, "_registered", {**backends._registered, "failing": Failing()})
    run = project.new_run()
    with pytest.raises(SolverError, match="diverged"):
        execute(run, project.load_scene(), backend="failing")
    assert run.state == "failed"
    assert run.message == "diverged after 3 iterations"
    assert "failing solver: starting" in run.log_path.read_text()


def test_meshing_failure_is_recorded_before_any_problem_is_written(project):
    scene = project.load_scene()
    far = Circle("far", (9.0, 0.0), 0.5)
    scene.shapes.append(far)
    scene.regions.append(Region("island", far, {"epsilon": 1.0}))
    run = project.new_run()
    with pytest.raises(MeshError, match="one connected piece"):
        execute(run, scene)
    assert run.state == "failed"
    assert not run.problem_path.exists()


def test_a_run_state_is_running_while_it_works(project):
    run = project.new_run()
    seen = []
    execute(run, project.load_scene(), on_log=lambda line: seen.append(run.state))
    assert set(seen) == {"running"}
    assert run.state == "success"
