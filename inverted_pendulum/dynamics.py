"""Cart-pole dynamics: nonlinear equations of motion and their linearization.

State vector convention used throughout this project:
    z = [x, x_dot, theta, theta_dot]
where x is cart position, theta is pole angle measured from the upright
(unstable) equilibrium, theta = 0.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class CartPoleParams:
    M: float = 1.0      # cart mass (kg)
    m: float = 0.1       # pole point mass (kg)
    l: float = 0.5       # pole length, pivot to bob (m)
    g: float = 9.81      # gravity (m/s^2)
    b: float = 0.0       # cart viscous friction coefficient (0 = frictionless)
    c: float = 0.0       # pole pivot viscous friction coefficient (0 = frictionless)


def nonlinear_dynamics(t: float, z: np.ndarray, u: float, params: CartPoleParams) -> np.ndarray:
    """Right-hand side of the nonlinear cart-pole ODE: returns z_dot given (t, z, u).

    `t` is unused (the system is time-invariant) but kept so this function
    matches the signature scipy.integrate.solve_ivp expects for its `fun`
    argument.

    Use Euler - Lagrange equations to derive the values for double dot of x theta"""
    M, m, l, g, b, c = params.M, params.m, params.l, params.g, params.b, params.c
    x, x_dot, theta, theta_dot = z
    cos = np.cos(theta)
    sin = np.sin(theta)
    lhs = np.array([[cos,l],[(m+M)/(m*l),cos]])
    rhs = np.array([-c/(m*l)*theta_dot + g*sin,(u-b*x_dot)/(m*l)+sin*theta_dot**2])

    xddot, thetaddot = np.linalg.solve(lhs,rhs)

    return np.array([x_dot,xddot,theta_dot,thetaddot])


def linearize(params: CartPoleParams) -> tuple[np.ndarray, np.ndarray]:
    """Linearize the dynamics about the upright equilibrium (theta=0, all else 0).

    Returns (A, B) such that, near the equilibrium, z_dot ~= A @ z + B @ u.

    TODO: implement using the analytic small-angle linearization of the
    equations of motion above.
    """
    M, m, l, g, b, c = params.M, params.m, params.l, params.g, params.b, params.c

    A = np.array([[0,1,0,0],[0,-b/M,-m*g/M,c/(M*l)],[0,0,0,1],[0,b/(M*l),g*(m+M)/(M*l),-(M+m)*c/(m*M*l**2)]])
    B = np.array([0,1/M,0,-1/(M*l)])
    B = B.reshape(-1,1)

    return A,B


def energy(z: np.ndarray, params: CartPoleParams) -> float:
    """Total mechanical energy (kinetic + potential) of the cart-pole system.

    Useful as a sanity check: with u=0 and no damping (b=c=0), this should
    stay constant along any trajectory.

    TODO: implement T + V using the same kinematics as the Lagrangian above.
    """
    M, m, l, g, b, c = params.M, params.m, params.l, params.g, params.b, params.c
    x,x_dot,theta,theta_dot = z

    T = 0.5*M*x_dot**2+0.5*m*(x_dot**2+2*l*np.cos(theta)*x_dot*theta_dot+l**2*theta_dot**2)
    V = m*g*l*np.cos(theta)
    return T+V
