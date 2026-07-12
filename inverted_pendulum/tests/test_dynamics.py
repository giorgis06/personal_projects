"""Sanity checks for dynamics.py and controller.py.

These aren't just "does it run" tests -- each one verifies a specific
property your equations of motion / LQR gain must have. If one fails,
it's telling you something concrete about which part of the derivation
or code to revisit.
"""

import numpy as np
import pytest

from dynamics import CartPoleParams, nonlinear_dynamics, linearize, energy
from controller import lqr, closed_loop_eigs

PARAMS = CartPoleParams()


def test_equilibrium_is_a_fixed_point():
    z = np.zeros(4)
    zdot = nonlinear_dynamics(0.0, z, 0.0, PARAMS)
    assert np.allclose(zdot, 0.0, atol=1e-10)


def test_linearization_matches_finite_difference_jacobian():
    A, B = linearize(PARAMS)

    eps = 1e-6
    z0 = np.zeros(4)
    u0 = 0.0

    A_fd = np.zeros((4, 4))
    for i in range(4):
        dz = np.zeros(4)
        dz[i] = eps
        f_plus = nonlinear_dynamics(0.0, z0 + dz, u0, PARAMS)
        f_minus = nonlinear_dynamics(0.0, z0 - dz, u0, PARAMS)
        A_fd[:, i] = (f_plus - f_minus) / (2 * eps)

    f_plus = nonlinear_dynamics(0.0, z0, u0 + eps, PARAMS)
    f_minus = nonlinear_dynamics(0.0, z0, u0 - eps, PARAMS)
    B_fd = ((f_plus - f_minus) / (2 * eps)).reshape(4, 1)

    assert np.allclose(A, A_fd, atol=1e-4), f"A mismatch:\n{A}\nvs finite-diff:\n{A_fd}"
    assert np.allclose(B, B_fd, atol=1e-4), f"B mismatch:\n{B}\nvs finite-diff:\n{B_fd}"


def test_system_is_controllable():
    A, B = linearize(PARAMS)
    ctrb = np.hstack([B, A @ B, A @ A @ B, A @ A @ A @ B])
    assert np.linalg.matrix_rank(ctrb) == 4


def test_lqr_gain_stabilizes_linearized_system():
    A, B = linearize(PARAMS)
    Q = np.diag([1.0, 1.0, 10.0, 1.0])
    R = np.array([[0.1]])
    K, _P = lqr(A, B, Q, R)
    eigs = closed_loop_eigs(A, B, K)
    assert np.all(np.real(eigs) < 0), f"unstable closed-loop eigenvalues: {eigs}"


def test_energy_is_conserved_without_control_or_damping():
    params = CartPoleParams(b=0.0, c=0.0)
    z0 = np.array([0.0, 0.0, 0.3, 0.0])
    from scipy.integrate import solve_ivp

    sol = solve_ivp(
        lambda t, z: nonlinear_dynamics(t, z, 0.0, params),
        (0.0, 3.0), z0, method="RK45", max_step=0.01,
    )
    energies = np.array([energy(z, params) for z in sol.y.T])
    e0 = energies[0]
    assert np.max(np.abs(energies - e0)) < 1e-3 * abs(e0)
