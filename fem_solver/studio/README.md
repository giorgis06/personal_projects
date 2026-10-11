# FEM Studio

Desktop front end for the solver in `fem_solver/`. The plan is in [ORCHESTRATOR.md](ORCHESTRATOR.md).

## Setup

From `fem_solver/`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r studio/requirements.txt
```

## Run

From `fem_solver/studio/`:

```bash
../.venv/bin/python -m femstudio
```

## Test and lint

From `fem_solver/studio/`:

```bash
../.venv/bin/python -m pytest -m "not ui and not real_solver"   # as in CI
../.venv/bin/python -m pytest -m ui                              # window tests, offscreen
ruff check . && ruff format --check .
```

To run the window tests on screen: `QT_QPA_PLATFORM=xcb ../.venv/bin/python -m pytest -m ui`.
