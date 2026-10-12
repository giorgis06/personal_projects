import math

import numpy as np
from femstudio.core.project.run import RunResult

A, B, R = 0.2, 0.5, 2.0
EPS_GLASS, EPS_AIR, VOLTS = 4.0, 1.0, 5.0


def analytic_potential(r: np.ndarray) -> np.ndarray:
    """The capacitor's potential: u = V at r = a, 0 at r = R, flux eps r du/dr continuous at b."""
    charge = VOLTS / (math.log(R / B) / EPS_AIR + math.log(B / A) / EPS_GLASS)
    inside = VOLTS - charge / EPS_GLASS * np.log(np.maximum(r, A) / A)
    outside = charge / EPS_AIR * np.log(R / np.maximum(r, B))
    return np.where(r <= B, inside, outside)


def check_against_analytic(result: RunResult, tolerance: float) -> None:
    r = np.linalg.norm(result.mesh.nodes, axis=1)
    error = np.abs(result.solution.values - analytic_potential(r)).max()
    assert error < tolerance, f"largest error {error:.3g} exceeds {tolerance}"
