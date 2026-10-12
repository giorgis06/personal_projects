import json
from pathlib import Path

import numpy as np
import pytest
from examples.capacitor import capacitor_scene
from femstudio.backends import registry as backends
from femstudio.backends.base import SolverBackend, SolverError
from femstudio.core.mesh.mesher import MeshError
from femstudio.core.project.project import Project
from femstudio.core.results.reader import ResultError, RunInfo
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
    loaded = project.run(run.number).load_result(physics.get("electrostatics"))
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


def test_a_run_keeps_the_scene_it_was_solved_with(project):
    run = project.new_run()
    execute(run, project.load_scene())
    changed = project.load_scene()
    changed.regions[0].material["epsilon"] = ((40.0, 0.0), (0.0, 40.0))
    changed.regions[0].name = "quartz"
    project.save_scene(changed)

    loaded = project.run(run.number).load_result(physics.get("electrostatics"))
    assert loaded.scene == capacitor_scene()
    density = physics.get("electrostatics").derive(loaded.scene, loaded.mesh, loaded.solution)
    assert np.isfinite(density["energy_density"].values).all()
    assert run.load_scene().region("glass").material["epsilon"] == ((4.0, 0.0), (0.0, 4.0))


def test_the_scene_is_saved_even_when_the_run_fails(project):
    scene = project.load_scene()
    far = Circle("far", (9.0, 0.0), 0.5)
    scene.shapes.append(far)
    scene.regions.append(Region("island", far, {"epsilon": 1.0}))
    run = project.new_run()
    with pytest.raises(MeshError):
        execute(run, scene)
    assert run.load_scene() == scene


def test_the_solved_field_takes_its_name_and_unit_from_the_problem_type(project):
    run = project.new_run()
    result = execute(run, project.load_scene())
    spec = next(o for o in physics.get("electrostatics").output_fields if not o.derived)
    assert (result.solution.name, result.solution.unit) == (spec.name, spec.unit)


def test_a_second_execute_never_reports_the_previous_result(project, monkeypatch):
    class Silent(SolverBackend):
        name = "silent"
        supported_problem_types = ("*",)

        def is_available(self):
            return True

        def solve(self, run_folder, on_log):
            return RunInfo("success", 0, 0.0, {}, "wrote nothing")

    monkeypatch.setattr(backends, "_registered", {**backends._registered, "silent": Silent()})
    run = project.new_run()
    execute(run, project.load_scene())
    assert (run.result_dir / "solution.csv").is_file()
    with pytest.raises(ResultError, match="solution.csv is missing"):
        execute(run, project.load_scene(), backend="silent")
    assert run.state == "failed"
    assert not run.result_dir.exists()


def test_relative_project_path_gives_absolute_folders(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project = Project.create(Path("rel"), capacitor_scene())
    run = project.new_run()
    assert project.folder.is_absolute() and run.folder.is_absolute()
    execute(run, project.load_scene())
    assert run.state == "success"


def test_stray_entries_do_not_break_the_run_list(project):
    first = project.new_run()
    runs_dir = project.folder / "runs"
    (runs_dir / "run_backup").mkdir()
    (runs_dir / "run_").mkdir()
    (runs_dir / "run_007.txt").write_text("notes")
    (runs_dir / "notes").mkdir()
    assert [run.number for run in project.runs()] == [1]
    assert project.new_run().number == 2
    assert first.number == 1


def test_an_unreadable_status_file_counts_as_failed(project):
    run = project.new_run()
    (run.folder / "status.json").write_text('{"state": "succ')
    assert run.state == "failed"
    assert "cannot be read" in run.message


def test_a_run_that_ended_unfinished_is_recorded_as_failed(project):
    run = project.new_run()
    assert run.state == "created"
    run.abandon("stopped by the user")
    assert (run.state, run.message) == ("failed", "stopped by the user")


def test_abandoning_leaves_a_finished_run_as_it_was(project):
    run = project.new_run()
    execute(run, project.load_scene())
    run.abandon("stopped by the user")
    assert run.state == "success"
