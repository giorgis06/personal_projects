import numpy as np
import pytest
from examples.capacitor import capacitor_scene
from femstudio.backends import registry as backends
from femstudio.core.project.loaded_run import load_result_set
from femstudio.core.project.project import Project
from femstudio.core.results.reader import ResultError
from femstudio.physics import registry as physics


@pytest.fixture
def run(tmp_path):
    project = Project.create(tmp_path / "proj", capacitor_scene())
    run = project.new_run()
    problem = physics.get("electrostatics")
    run.execute(project.load_scene(), problem, backends.get("mock"), size=0.2)
    return run


def test_a_finished_run_loads_with_its_solved_and_derived_fields(run):
    results = load_result_set(run, physics.get("electrostatics"))
    assert results.run_number == run.number
    assert results.names() == ["u", "E", "E_magnitude", "energy_density"]
    assert results.label("E_magnitude") == "Field magnitude"
    assert results.unit("u") == "V"
    assert len(results.scalars("u")) == results.mesh.n_nodes
    assert len(results.scalars("energy_density")) == results.mesh.n_triangles


def test_the_derived_magnitude_matches_the_field_it_comes_from(run):
    results = load_result_set(run, physics.get("electrostatics"))
    np.testing.assert_allclose(
        results.scalars("E"), results.fields["E_magnitude"].values, rtol=1e-12
    )


def test_a_run_with_no_result_cannot_be_loaded(tmp_path):
    project = Project.create(tmp_path / "proj", capacitor_scene())
    run = project.new_run()
    with pytest.raises((ResultError, OSError, ValueError)):
        load_result_set(run, physics.get("electrostatics"))
