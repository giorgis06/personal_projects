"""CLI entry point: derive the LQR gain, simulate, animate, and plot the cart-pole system."""

import argparse
import os

import numpy as np
import matplotlib.pyplot as plt

from dynamics import CartPoleParams, linearize
from controller import lqr
from simulate import simulate_nonlinear, simulate_linear
from animate import animate_cartpole
from plots import plot_states, plot_phase_portrait, plot_linear_vs_nonlinear


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cart-pole inverted pendulum LQR simulation")
    parser.add_argument("--theta0", type=float, default=0.1, help="initial pole angle (rad)")
    parser.add_argument("--x0", type=float, default=0.0, help="initial cart position (m)")
    parser.add_argument("--t-final", type=float, default=8.0, help="simulation duration (s)")
    parser.add_argument("--dt", type=float, default=0.02, help="sample/frame spacing (s)")
    parser.add_argument(
        "--compare-linear", action="store_true",
        help="also simulate the linearized closed loop with the same K and plot the divergence",
    )
    parser.add_argument(
        "--save-animation", type=str, default=None, metavar="PATH",
        help="write the cart-pole animation to PATH as a .gif",
    )
    parser.add_argument(
        "--save-plots", type=str, default=None, metavar="DIR",
        help="write the analysis plots (states, phase portrait, and comparison if requested) to DIR as PNGs",
    )
    parser.add_argument("--no-show", action="store_true", help="don't open interactive plot windows")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    params = CartPoleParams()
    A, B = linearize(params)
    Q = np.diag([1.0, 1.0, 10.0, 1.0])
    R = np.array([[0.1]])
    K, _P = lqr(A, B, Q, R)

    z0 = np.array([args.x0, 0.0, args.theta0, 0.0])
    z_ref = np.zeros(4)
    t_span = (0.0, args.t_final)

    t, Z_nl, _U_nl = simulate_nonlinear(params, K, z0, z_ref, t_span, args.dt)
    if t[-1] < args.t_final - args.dt:
        print(
            f"warning: nonlinear plant diverged at t={t[-1]:.3f}s (requested {args.t_final}s) -- "
            "the LQR gain, derived from the small-angle linearization, failed to recover "
            "the true nonlinear plant from this initial angle."
        )

    if args.save_animation is not None:
        os.makedirs(os.path.dirname(args.save_animation) or ".", exist_ok=True)
    # keep a reference alive -- FuncAnimation stops (or never renders) if it's
    # garbage-collected before plt.show() runs the event loop
    anim = animate_cartpole(t, Z_nl, params, save_path=args.save_animation)

    if args.save_plots is not None:
        os.makedirs(args.save_plots, exist_ok=True)

    fig_states = plot_states(t, Z_nl, title="Nonlinear closed-loop response")
    fig_phase = plot_phase_portrait(Z_nl)
    if args.save_plots is not None:
        fig_states.savefig(os.path.join(args.save_plots, "states.png"), dpi=150)
        fig_phase.savefig(os.path.join(args.save_plots, "phase.png"), dpi=150)

    if args.compare_linear:
        _t_lin, Z_lin, _U_lin = simulate_linear(A, B, K, z0, z_ref, t_span, args.dt)
        # both trajectories are sampled on the same t_eval grid, but the nonlinear
        # one may terminate early if it diverges -- truncate to the common length
        fig_compare = plot_linear_vs_nonlinear(t, Z_lin[: len(t)], Z_nl)
        if args.save_plots is not None:
            fig_compare.savefig(os.path.join(args.save_plots, "compare.png"), dpi=150)

    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
