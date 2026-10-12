import math

import numpy as np
import pytest
from examples.capacitor import capacitor_scene
from femstudio.backends.executable import ExecutableBackend
from femstudio.core.project.project import Project
from femstudio.physics import registry as physics
from tests.backends.capacitor_oracle import (
    EPS_AIR,
    EPS_GLASS,
    VOLTS,
    A,
    B,
    R,
    analytic_potential,
    check_against_analytic,
)


def test_analytic_potential_meets_its_boundary_and_interface_conditions():
    u = analytic_potential(np.array([A, B, R]))
    assert u[0] == pytest.approx(VOLTS)
    assert u[2] == pytest.approx(0.0, abs=1e-12)
    # the potential is continuous at the glass-air interface, from either side
    charge = VOLTS / (math.log(R / B) / EPS_AIR + math.log(B / A) / EPS_GLASS)
    assert u[1] == pytest.approx(charge * math.log(R / B) / EPS_AIR)
    assert u[1] == pytest.approx(VOLTS - charge * math.log(B / A) / EPS_GLASS)


def run_capacitor(tmp_path, backend, size):
    project = Project.create(tmp_path / "proj", capacitor_scene())
    return project.new_run().execute(
        project.load_scene(), physics.get("electrostatics"), backend, size=size
    )


def test_the_fake_solver_in_capacitor_mode_passes_the_acceptance_check(
    tmp_path, fake_fem, monkeypatch
):
    monkeypatch.setenv("FAKE_FEM_MODE", "capacitor")
    result = run_capacitor(tmp_path, ExecutableBackend(fake_fem), 0.1)
    check_against_analytic(result, tolerance=1e-9)


def test_the_acceptance_check_rejects_a_wrong_field(tmp_path, fake_fem):
    result = run_capacitor(tmp_path, ExecutableBackend(fake_fem), 0.2)
    with pytest.raises(AssertionError, match="exceeds"):
        check_against_analytic(result, tolerance=1e-3)
