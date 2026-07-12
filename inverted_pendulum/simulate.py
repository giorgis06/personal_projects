"""Time-integration helpers: run the nonlinear or linear closed-loop cart-pole system."""

from typing import Optional

import numpy as np
from scipy.integrate import solve_ivp

from dynamics import CartPoleParams, nonlinear_dynamics


def _lqr_control(z: np.ndarray, z_ref: np.ndarray, K: np.ndarray) -> float:
    return float(-K @ (z - z_ref))


_BLOWUP_THRESHOLD = 1e3


def _blowup_event(t: float, z: np.ndarray) -> float:
    """Zero-crossing event: fires once any state component exceeds a sane
    physical range, so runs where the fixed LQR gain fails far from its
    linearization point terminate quickly instead of forcing the adaptive
    integrator to grind through a near-singular blow-up.
    """
    return _BLOWUP_THRESHOLD - np.max(np.abs(z))


_blowup_event.terminal = True


def simulate_nonlinear(
    params: CartPoleParams,
    K: np.ndarray,
    z0: np.ndarray,
    z_ref: np.ndarray,
    t_span: tuple[float, float],
    dt: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Simulate the true nonlinear plant under LQR state feedback u = -K(z - z_ref).

    Returns (t, Z, U) where Z has shape (len(t), 4) and U has shape (len(t),).
    """
    t_eval = np.arange(t_span[0], t_span[1] + dt, dt)

    def rhs(t: float, z: np.ndarray) -> np.ndarray:
        u = _lqr_control(z, z_ref, K)
        return nonlinear_dynamics(t, z, u, params)

    sol = solve_ivp(
        rhs, t_span, z0, method="RK45", t_eval=t_eval,
        dense_output=False, events=_blowup_event,
    )
    Z = sol.y.T
    U = np.array([_lqr_control(z, z_ref, K) for z in Z])
    return sol.t, Z, U


def simulate_linear(
    A: np.ndarray,
    B: np.ndarray,
    K: np.ndarray,
    z0: np.ndarray,
    z_ref: np.ndarray,
    t_span: tuple[float, float],
    dt: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Simulate the linearized closed-loop system z_dot = (A - B K)(z - z_ref) about z_ref.

    Uses the same K as simulate_nonlinear so the two trajectories are directly
    comparable (see plots.plot_linear_vs_nonlinear).
    """
    t_eval = np.arange(t_span[0], t_span[1] + dt, dt)
    A_cl = A - B @ K

    def rhs(t: float, z: np.ndarray) -> np.ndarray:
        return A_cl @ (z - z_ref)

    sol = solve_ivp(
        rhs, t_span, z0, method="RK45", t_eval=t_eval,
        dense_output=False, events=_blowup_event,
    )
    Z = sol.y.T
    U = np.array([_lqr_control(z, z_ref, K) for z in Z])
    return sol.t, Z, U
