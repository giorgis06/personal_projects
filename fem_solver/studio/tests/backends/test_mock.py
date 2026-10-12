import numpy as np
import pytest
from examples.capacitor import capacitor_scene
from femstudio.backends.base import SolverError
from femstudio.backends.mock import MockBackend
from femstudio.core.mesh.mesher import mesh_scene
from femstudio.core.results.reader import read_run_info, read_solution
from femstudio.physics import registry as physics


@pytest.fixture
def run_folder(tmp_path):
    scene = capacitor_scene()
    mesh = mesh_scene(scene, 0.2, tmp_path / "mesh.msh")
    physics.get("electrostatics").write_problem(scene, mesh, tmp_path)
    return tmp_path, mesh


def test_field_is_the_cosine_bump_over_the_bounding_box(run_folder):
    folder, mesh = run_folder
    MockBackend().solve(folder, lambda line: None)
    field = read_solution(folder / "result", mesh, name="u", unit="V")
    x, y = mesh.nodes.T
    (x0, x1), (y0, y1) = (x.min(), x.max()), (y.min(), y.max())
    expected = np.cos(np.pi * (x - (x0 + x1) / 2) / (x1 - x0)) * np.cos(
        np.pi * (y - (y0 + y1) / 2) / (y1 - y0)
    )
    np.testing.assert_allclose(field.values, expected, atol=1e-12)
    # the capacitor spans [-2, 2] on both axes, to within the polygonal circle's chord
    nominal = np.cos(np.pi * x / 4) * np.cos(np.pi * y / 4)
    np.testing.assert_allclose(field.values, nominal, atol=5e-3)


def test_run_info_says_it_is_not_a_solution(run_folder):
    folder, _ = run_folder
    info = MockBackend().solve(folder, lambda line: None)
    assert info.status == "success"
    assert "not a solution" in info.message
    assert read_run_info(folder / "result") == info


def test_logs_progress(run_folder):
    folder, _ = run_folder
    lines = []
    MockBackend().solve(folder, lines.append)
    assert len(lines) >= 2 and all(line.startswith("mock solver") for line in lines)


def test_supports_any_problem_type_and_is_available():
    backend = MockBackend()
    assert backend.is_available()
    assert backend.supports("electrostatics") and backend.supports("anything_else")


def test_without_a_problem_file(tmp_path):
    with pytest.raises(SolverError, match="problem.json is not in"):
        MockBackend().solve(tmp_path, lambda line: None)


def test_without_a_mesh(tmp_path):
    (tmp_path / "problem.json").write_text("{}")
    with pytest.raises(SolverError, match="no such file"):
        MockBackend().solve(tmp_path, lambda line: None)
