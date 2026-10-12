import os

import pytest
from examples.capacitor import capacitor_scene
from femstudio.backends.executable import ENVIRONMENT_VARIABLE, ExecutableBackend
from femstudio.core.project.project import Project
from femstudio.physics import registry as physics
from tests.backends.capacitor_oracle import check_against_analytic

pytestmark = [
    pytest.mark.real_solver,
    pytest.mark.skipif(
        not os.environ.get(ENVIRONMENT_VARIABLE),
        reason=f"set {ENVIRONMENT_VARIABLE} to a fem build that has the command-line interface",
    ),
]


def test_capacitor_through_the_real_solver_matches_the_analytic_solution(tmp_path):
    backend = ExecutableBackend()
    assert backend.is_available()
    project = Project.create(tmp_path / "proj", capacitor_scene())
    result = project.new_run().execute(
        project.load_scene(), physics.get("electrostatics"), backend, size=0.02
    )
    # linear elements on a 0.02 mesh: the error is of order h^2 times the field's curvature
    check_against_analytic(result, tolerance=2e-2)
