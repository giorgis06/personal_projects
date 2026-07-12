"""Static analysis plots: state trajectories, phase portraits, linear-vs-nonlinear comparison."""

import numpy as np
import matplotlib.pyplot as plt

STATE_LABELS = ["x (m)", "x_dot (m/s)", "theta (rad)", "theta_dot (rad/s)"]


def plot_states(t: np.ndarray, Z: np.ndarray, title: str = "State trajectories"):
    fig, axes = plt.subplots(4, 1, figsize=(8, 9), sharex=True)
    for i, ax in enumerate(axes):
        ax.plot(t, Z[:, i])
        ax.set_ylabel(STATE_LABELS[i])
        ax.grid(True, alpha=0.3)
    axes[-1].set_xlabel("t (s)")
    fig.suptitle(title)
    fig.tight_layout()
    return fig


def plot_phase_portrait(Z: np.ndarray, title: str = "Phase portrait: theta vs theta_dot"):
    fig, ax = plt.subplots(figsize=(6, 6))
    theta, theta_dot = Z[:, 2], Z[:, 3]
    ax.plot(theta, theta_dot, linewidth=1.5)
    ax.plot(theta[0], theta_dot[0], "go", label="start")
    ax.plot(theta[-1], theta_dot[-1], "rx", label="end")
    ax.set_xlabel("theta (rad)")
    ax.set_ylabel("theta_dot (rad/s)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    return fig


def plot_linear_vs_nonlinear(t: np.ndarray, Z_lin: np.ndarray, Z_nl: np.ndarray):
    """Overlay the linear-model-predicted and true-nonlinear-plant trajectories
    under the same fixed LQR gain, to show where the linearization stops
    being a good approximation.
    """
    fig, axes = plt.subplots(4, 1, figsize=(8, 9), sharex=True)
    for i, ax in enumerate(axes):
        ax.plot(t, Z_lin[:, i], "--", label="linear model", color="tab:orange")
        ax.plot(t, Z_nl[:, i], "-", label="nonlinear plant", color="tab:blue")
        ax.set_ylabel(STATE_LABELS[i])
        ax.grid(True, alpha=0.3)
    axes[0].legend()
    axes[-1].set_xlabel("t (s)")
    fig.suptitle("Linear model vs. true nonlinear plant (same LQR gain K)")
    fig.tight_layout()
    return fig
