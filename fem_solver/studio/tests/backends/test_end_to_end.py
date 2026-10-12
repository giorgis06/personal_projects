import numpy as np
from examples.capacitor import capacitor_scene
from femstudio.backends.executable import ExecutableBackend
from femstudio.core.project.project import Project
from femstudio.physics import registry as physics


def test_executable_backend_runs_a_project_end_to_end(tmp_path, fake_fem):
    project = Project.create(tmp_path / "proj", capacitor_scene())
    run = project.new_run()
    result = run.execute(
        project.load_scene(),
        physics.get("electrostatics"),
        ExecutableBackend(fake_fem),
        size=0.2,
    )
    x, y = result.mesh.nodes.T
    np.testing.assert_allclose(result.solution.values, x + 2.0 * y)
    assert run.state == "success"
    assert "fake fem: cg iteration 7 residual 1e-11" in run.log_path.read_text()
