"""LQR controller design for the linearized cart-pole system.

This file is the control-theory core of the project -- fill in the TODOs
yourself. See the accompanying walkthrough for the Riccati-equation /
LQR derivation.
"""

import numpy as np
import scipy.linalg


def lqr(A: np.ndarray, B: np.ndarray, Q: np.ndarray, R: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute the infinite-horizon continuous-time LQR gain K and Riccati solution P.

    Given the linear system z_dot = A @ z + B @ u, and cost
    J = integral( z^T Q z + u^T R u ) dt, returns (K, P) such that the
    optimal control is u = -K @ z, where P solves the continuous algebraic
    Riccati equation A^T P + P A - P B R^-1 B^T P + Q = 0.

    TODO: solve the Riccati equation (scipy.linalg.solve_continuous_are is
    the relevant solver) and derive K from P.
    """

    P = scipy.linalg.solve_continuous_are(A,B,Q,R)
    K = np.linalg.inv(R)@B.T@P
    return K,P


def closed_loop_eigs(A: np.ndarray, B: np.ndarray, K: np.ndarray) -> np.ndarray:
    """Eigenvalues of the closed-loop system matrix (A - B @ K).

    All eigenvalues should have negative real part for the closed loop to
    be stable -- this is the certificate that your LQR gain actually
    stabilizes the linearized system.

    TODO: implement.
    """

    return np.linalg.eigvals(A-B@K)
    raise NotImplementedError("Implement the closed-loop eigenvalue check")
