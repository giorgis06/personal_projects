# Cart-Pole Inverted Pendulum

A cart-pole (inverted pendulum on a cart) simulation with an LQR stabilizing
controller, built to accompany a first course in state-space / dynamic
systems.

## Model

- Cart of mass `M` on a frictionless (or optionally lightly damped)
  horizontal rail, driven by force `u`.
- Pole of length `l` with point mass `m` at the tip, pivoted on the cart.
- `theta` is measured from the **upright** position (`theta = 0`), the
  unstable equilibrium we want to stabilize.
- State vector: `z = [x, x_dot, theta, theta_dot]`.

The nonlinear equations of motion and their linearization about the upright
equilibrium are implemented in `dynamics.py`. The LQR gain (via the
continuous algebraic Riccati equation) is implemented in `controller.py`.
Both of those files are meant to be worked through by hand as a learning
exercise -- see the TODOs inside them.

## Setup

Requires `python3-venv`/`pip` to be available system-wide (on Debian/Ubuntu:
`sudo apt install -y python3-pip python3-venv`, one-time, if not already
installed). Then, from this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Every command below assumes the venv is activated (`source .venv/bin/activate`).
If you'd rather not activate it, prefix each command with `.venv/bin/` instead
(e.g. `.venv/bin/python main.py ...`).

## Running the simulation

```bash
# Small initial disturbance: stabilizes cleanly. Opens two plot windows
# (state trajectories + phase portrait) and an animation window.
python main.py --theta0 0.1

# Also simulate the linearized model side by side, to compare against
# the true nonlinear plant under the same LQR gain:
python main.py --theta0 0.1 --compare-linear
```

To save the results as files instead of (or in addition to) opening windows:

```bash
python main.py --theta0 0.1 --compare-linear \
  --save-animation outputs/demo.gif \
  --save-plots outputs \
  --no-show
```

This writes `outputs/demo.gif` (the animated cart-pole) and
`outputs/states.png`, `outputs/phase.png`, `outputs/compare.png` (the
analysis plots) without popping up any windows. `outputs/` is gitignored, so
these are safe to regenerate freely.

**Watch the linearization break down** by increasing `--theta0` (radians).
Stabilizes fine through about `1.0`-`1.1`; by `1.2`-`1.3` the true nonlinear
plant diverges outright even though the linear model still predicts
recovery, since the LQR gain was only derived from the small-angle
approximation:

```bash
python main.py --theta0 1.0 --compare-linear --no-show --save-plots outputs
python main.py --theta0 1.3 --compare-linear --no-show --save-plots outputs   # diverges
```

When it diverges, `main.py` prints a warning and the run stops early rather
than hanging.

All CLI options:

| flag | default | meaning |
| --- | --- | --- |
| `--theta0` | `0.1` | initial pole angle (rad) |
| `--x0` | `0.0` | initial cart position (m) |
| `--t-final` | `8.0` | simulation duration (s) |
| `--dt` | `0.02` | sample/animation frame spacing (s) |
| `--compare-linear` | off | also simulate the linearized model with the same `K` |
| `--save-animation PATH` | none | write the cart-pole animation to `PATH` as a `.gif` |
| `--save-plots DIR` | none | write `states.png`/`phase.png`/`compare.png` to `DIR` |
| `--no-show` | off | don't open interactive plot/animation windows |

Run `python main.py --help` for the same summary from argparse.

## Tests

```bash
pytest tests/
```

Checks: the origin is a fixed point of the nonlinear dynamics, the analytic
linearization matches a finite-difference Jacobian, the linear system is
controllable, the LQR gain stabilizes it (closed-loop eigenvalues have
negative real part), and energy is conserved for the undriven, undamped
system (a strong check that the equations of motion are correct).

## Tuning

`Q = diag([1, 1, 10, 1])` and `R = [[0.1]]` in `main.py` are starting
weights, not gospel -- the classic LQR trade-off applies: larger `R` gives
gentler/slower control effort, a larger `theta` weight in `Q` gives a
faster/more aggressive angle correction.

## Extensions

- Implement your own fixed-step RK4 integrator and compare its trajectory
  against `scipy.integrate.solve_ivp`.
- Add cart-rail damping (`b`) or pivot damping (`c`) and see how the
  dynamics/energy-conservation test needs to change.
- Try pole placement instead of LQR for the gain `K` and compare behavior.
