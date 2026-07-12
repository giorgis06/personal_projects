"""Animated cart-pole visualization."""

from typing import Optional

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Rectangle

from dynamics import CartPoleParams

CART_WIDTH = 0.3
CART_HEIGHT = 0.15


def animate_cartpole(
    t: np.ndarray,
    Z: np.ndarray,
    params: CartPoleParams,
    save_path: Optional[str] = None,
    fps: int = 50,
) -> FuncAnimation:
    """Animate cart position x(t) and pole angle theta(t) from a simulated trajectory.

    Z has columns [x, x_dot, theta, theta_dot]. If save_path is given, writes
    a .gif there (via Pillow, no ffmpeg dependency) instead of/in addition to
    showing it interactively.
    """
    x = Z[:, 0]
    theta = Z[:, 2]
    pole_tip_x = x + params.l * np.sin(theta)
    pole_tip_y = params.l * np.cos(theta)

    track_margin = 1.0
    x_min, x_max = float(np.min(x)) - track_margin, float(np.max(x)) + track_margin

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(-0.2, params.l * 1.3)
    ax.set_aspect("equal")
    ax.axhline(0.0, color="gray", linewidth=1, zorder=0)
    ax.set_title("Cart-Pole")
    ax.set_xlabel("x (m)")

    cart_patch = Rectangle(
        (x[0] - CART_WIDTH / 2, -CART_HEIGHT / 2), CART_WIDTH, CART_HEIGHT,
        facecolor="steelblue", edgecolor="black", zorder=2,
    )
    ax.add_patch(cart_patch)
    (pole_line,) = ax.plot([], [], "o-", color="firebrick", linewidth=3, markersize=6, zorder=3)
    time_text = ax.text(0.02, 0.92, "", transform=ax.transAxes)

    def init():
        cart_patch.set_xy((x[0] - CART_WIDTH / 2, -CART_HEIGHT / 2))
        pole_line.set_data([], [])
        time_text.set_text("")
        return cart_patch, pole_line, time_text

    def update(frame: int):
        cart_patch.set_xy((x[frame] - CART_WIDTH / 2, -CART_HEIGHT / 2))
        pole_line.set_data([x[frame], pole_tip_x[frame]], [0.0, pole_tip_y[frame]])
        time_text.set_text(f"t = {t[frame]:.2f}s")
        return cart_patch, pole_line, time_text

    interval_ms = 1000.0 / fps
    anim = FuncAnimation(fig, update, frames=len(t), init_func=init, interval=interval_ms, blit=True)

    if save_path is not None:
        anim.save(save_path, writer="pillow", fps=fps)

    return anim
