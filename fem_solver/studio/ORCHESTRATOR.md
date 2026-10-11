# FEM Studio: build plan

This file is the plan of record for a Python desktop app that sits in front of the C++ finite element solver in the parent folder (`fem_solver/`). Whoever builds a milestone reads this file first, works only inside `fem_solver/studio/`, and updates the status table at the bottom when a milestone is done.

## Goal

A user can open the app, look at an existing geometry or build a new one, assign materials and boundary conditions by name, mesh it, run a solver on it, and look at the result as a 2D heatmap and as a 3D surface. Adding a second kind of problem (magnetostatics, heat, waves) or a second solver (a Python reference solver, a GPU build) later should mean adding one new folder, not editing the existing ones.

The app is a front end over one data object, the **Scene**: geometry plus physics, with names as the only link between the two. Everything the window can do, a script or notebook must also be able to do by importing the same Scene classes with no window. The solver's README describes this idea under "Idea: defining problems easily"; read that section before starting.

## What exists today

Read these before writing anything:

- `fem_solver/README.md`: the maths, the layout, and the scene-file idea.
- `fem_solver/problem/`, `fem_solver/materials/`, `fem_solver/mesh/mesh.h`: what a problem consists of on the C++ side. A material is a symmetric 2x2 tensor per region, a boundary condition is Dirichlet, Neumann or Robin per boundary, the source is a function of (x, y).
- `fem_solver/meshes/cap.geo` and `fem_solver/tests/data/*.geo`: example geometries. Regions and boundaries are gmsh physical groups with names such as `"glass"`, `"inner_electrode"`.
- `fem_solver/requirements.txt` and `fem_solver/.venv`: Python 3.10 with numpy, scipy, matplotlib, meshio, pytest and gmsh 4.15.2 already installed.

Two facts that shape the plan:

1. **The `fem` executable cannot be driven from outside yet.** `main.cpp` hardcodes one mesh and one problem, takes no arguments, and writes no result file. The solve itself works (see `solver/electrostatics/solver.h` and the tests), but there is no command-line interface.
2. **The C++ code is the owner's own learning project.** Do not edit anything outside `fem_solver/studio/`. The command-line interface will be written by the owner against the contract below. Until then the app runs against the mock backend, and the executable backend is written and unit-tested against a fake executable.

## Hard rules

- Work only inside `fem_solver/studio/`. The one exception is adding lines to the repo's `.gitignore`.
- `core/`, `physics/` and `backends/` never import Qt or PyVista. Only `ui/` does. This is what keeps the Scene usable from a notebook and the logic testable without a display.
- The Scene and the window never show or store gmsh tag numbers. Names only. Tag numbers are assigned in one place, the mesher, when it writes the `.msh`.
- One concept per module, grouped into folders by meaning, following the C++ side (`mesh/`, `linalg/`, `problem/`, `solver/electrostatics/`). No module that mixes concerns, no `utils.py`, and split any file that grows past roughly 250 lines.
- A new problem type or backend is registered, never special-cased. No `if problem_type == "electrostatics"` outside `physics/electrostatics/`.
- Dependencies are limited to the list under "Stack". Ask before adding another.
- Generated files (meshes, results, project run folders) are never committed.
- The whole app is developed on the long-lived branch `ui/base-branch`, which is merged into `master` once, at the end. Each milestone is its own branch cut from `ui/base-branch` and lands as one pull request back into `ui/base-branch`. Never commit to `ui/base-branch` or `master` directly.
- Every milestone ends with `ruff check`, `ruff format --check` and `pytest` passing, and a short report of what was built, what was verified and how, and what was not verified.

## Stack

- Python 3.10, the existing `fem_solver/.venv`.
- **PySide6** for the window, **PyVista** with **pyvistaqt** for all rendering (geometry, mesh, heatmap, 3D surface). One rendering library for every view.
- **gmsh** Python API for geometry and meshing, **meshio** for reading meshes, **numpy**.
- **pytest**, plus **pytest-qt** for a few window smoke tests run offscreen.
- New dependencies go in `studio/requirements.txt`, not the parent file.

## Layout

```
fem_solver/studio/
  ORCHESTRATOR.md  BUILD_PROMPT.md  README.md  requirements.txt  pyproject.toml
  femstudio/
    __main__.py              python -m femstudio
    core/
      scene/                 the Scene: single source of truth
        shapes.py            Circle, Rectangle, Polygon (parametric, named)
        operations.py        union, difference, intersection
        region.py            a named area that will carry a material
        boundary.py          a named curve that will carry a boundary condition
        scene.py             Scene = shapes + regions + boundaries + physics values
        serialization.py     Scene <-> scene.json
        validation.py        checks listed under "Validation"
      expressions/
        grammar.py           the allowed expression language
        evaluate.py          parse, validate, evaluate on numpy arrays
      mesh/
        mesher.py            Scene -> gmsh model -> .msh, assigns tags from names
        mesh_data.py         nodes, triangles, named regions and edges as arrays
        reader.py            .msh / .geo -> MeshData
        quality.py           element quality statistics
      results/
        field.py             a named scalar or vector field on a mesh
        derived.py           E = -grad u, |E|, energy density
        reader.py            result folder -> fields + run metadata
      project/
        project.py           a folder on disk holding one scene and its runs
        run.py               one solve: inputs, outputs, log, status
    physics/
      base.py                ProblemType interface
      registry.py
      electrostatics/
        spec.py              material, boundary and source fields; output fields
        writer.py            Scene -> problem.json
    backends/
      base.py                SolverBackend interface
      registry.py
      executable.py          runs `fem problem.json`, streams the log
      mock.py                analytic field, no solver needed
    ui/
      main_window.py
      panels/                geometry, physics, mesh, solve, results (one file each)
      views/                 geometry_view, mesh_view, heatmap_view, surface_view
      widgets/               expression_edit, tensor_edit, log_view
      workers/               solve_worker (keeps the window responsive)
  tests/                     mirrors femstudio/ folder by folder
  examples/                  capacitor.py and capacitor.scene.json
```

The package is named `femstudio` and the folder `studio`; rename both together if the owner prefers another name.

## The two interfaces that make it extensible

**ProblemType** (`physics/base.py`) describes a kind of physics as data, so the window can build its forms without knowing the physics:

- `name`
- `material_fields`: what a region needs, with type and default (electrostatics: one symmetric 2x2 tensor `epsilon`)
- `boundary_kinds`: the allowed kinds and the fields each needs (dirichlet: `g`; neumann: `g`; robin: `g`, `kappa`)
- `source_fields` (electrostatics: `rho`)
- `output_fields`: what the solver returns and what can be derived from it
- `validate(scene)` and `write_problem(scene, mesh, folder)`

**SolverBackend** (`backends/base.py`):

- `name`, `supported_problem_types`
- `is_available()`: for the executable backend, whether the binary exists and accepts the contract
- `solve(run_folder, on_log)`: blocks, streams log lines, returns status; raises a typed error carrying the solver's message on failure

The panels are generated from the ProblemType. Nothing in `ui/` names a material property or a boundary kind literally.

## Solver contract (version 1, agreed with the owner)

The executable backend runs:

```
fem <run_folder>/problem.json
```

and expects exit code 0 on success, non-zero with a message on stderr on failure, and progress on stdout.

`problem.json`:

```json
{
  "schema_version": 1,
  "problem_type": "electrostatics",
  "mesh": "mesh.msh",
  "regions": {
    "glass": {"epsilon": [[4.0, 0.0], [0.0, 4.0]]},
    "air":   {"epsilon": [[1.0, 0.0], [0.0, 1.0]]}
  },
  "source": {"rho": "exp(-((x-1)^2 + y^2)/0.02)"},
  "boundaries": {
    "inner_electrode": {"kind": "dirichlet", "g": "5*cos(theta)"},
    "outer_wall":      {"kind": "dirichlet", "g": "0"}
  },
  "solver": {"method": "cg", "tolerance": 1e-10, "max_iterations": 10000},
  "output": "result"
}
```

- Keys under `regions` and `boundaries` are gmsh physical group names in the `.msh`.
- Every value that can vary in space is an expression string. The language is fixed in `core/expressions/grammar.py`: numbers, `+ - * / ^`, parentheses, variables `x y r theta`, constant `pi`, functions `sin cos tan exp log sqrt abs`. It is deliberately the subset that small C++ expression libraries accept.

Result, written by the solver into `<run_folder>/result/`:

- `solution.csv` with header `node_tag,u`: one row per mesh node, using the gmsh node tag from the `.msh`, so no ordering assumption is shared between the two programs.
- `run.json`: `{"status", "iterations", "residual", "timings": {...}, "message"}`.

`results/reader.py` is the only module that knows this format. A `.vtu` reader can be added beside it later without touching anything else.

## Validation

Run before meshing, shown in the window as a list with the offending name:

- every expression parses;
- every material tensor is symmetric positive definite;
- every region has a material;
- a boundary with no condition defaults to insulating (Neumann, g = 0), with a warning;
- no Dirichlet boundary at all is a warning (solution defined only up to a constant);
- names are unique and non-empty.

## Milestones

Each is one pull request and ends with a stop for review.

| # | Scope | Done when |
|---|---|---|
| M0 | Scaffold: folders, `pyproject.toml`, `requirements.txt`, ruff config, empty window that opens, README with run instructions | `python -m femstudio` opens a window; lint and an initial test pass |
| M1 | `core/scene`, `core/expressions`, serialization, validation | A scene built in code round-trips through `scene.json`; every validation rule has a passing and a failing test; no Qt import in `core/` (enforced by a test) |
| M2 | `core/mesh`: mesher, reader, quality | The capacitor scene meshes to a `.msh` whose physical names match the scene; `tests/data/*.geo` and `meshes/cap.geo` load into MeshData |
| M3 | `physics/`: interface, registry, electrostatics spec and `problem.json` writer | Written file matches the contract; schema covered by tests |
| M4 | `backends/`, `core/results`, `core/project` | Mock backend produces a field end to end; executable backend passes tests against a fake `fem` script covering success, failure and missing binary |
| M5 | Window shell and viewing: open `.geo` / `.msh` / project, geometry and mesh views, regions and boundaries coloured and listed by name | The capacitor opens and its named parts can be highlighted |
| M6 | Geometry editing: add shapes from forms, boolean operations, naming, live preview, undo | The capacitor can be rebuilt from an empty scene in the window |
| M7 | Physics, mesh and solve panels generated from the ProblemType; validation list; background solve with live log | A full run with the mock backend from the window, window stays responsive |
| M8 | Results: heatmap, 3D surface (height = value), mesh overlay, colour range control, field selector including derived fields, value probe on click | Both views show the same run; probe value matches the field array |
| M9 | Extras, chosen by the owner from the list below | per item |

## Proposed extras (for M9 and later)

- **Script export and import:** save the current scene as a Python script using the Scene classes, and load one back. The window and the notebook become two views of one thing.
- **Mesh refinement study:** run the same scene at halving mesh sizes and plot error or a chosen quantity against h. Matches the manufactured-solution tests the solver already uses.
- **Backend comparison:** run two backends on one scene and show the difference field. With a scipy reference backend added under `backends/`, this is a visual oracle for the C++ solver.
- **Line cut:** draw a segment, plot the field along it.
- **Field arrows and streamlines** for E.
- **Parameter sweep:** vary one number in the scene, collect a result quantity.
- **Run history:** every run kept in the project with its inputs, log and timings, reopenable. Later the natural place for CPU against GPU timing charts.
- **Export:** picture of the current view, `.vtu` of the result.

## Testing

Tests are how each milestone proves its "Done when" condition, so they are written with the code, not after it.

- **Where:** `studio/tests/` mirrors `femstudio/` folder by folder (`tests/core/scene/test_validation.py` tests `core/scene/validation.py`).
- **Two kinds, kept apart by a marker.** Tests of `core/`, `physics/` and `backends/` need no display and carry no marker. Tests that create a window carry `@pytest.mark.ui`, use pytest-qt with `QT_QPA_PLATFORM=offscreen`, and are limited to "opens, loads the example, does not raise". Register the marker in `pyproject.toml`.
- **What a test must check.** A real expected value, worked out independently of the code under test: a known area, a known node count for a fixed mesh size, a hand-written `problem.json`, an analytic field. A test that only checks "no exception" is acceptable for window smoke tests and nowhere else.
- **Every rule has a failing case.** Each validation rule, each backend error path (non-zero exit, missing binary, malformed result) and each expression-grammar rejection has a test that triggers it.
- **Architecture is tested too.** One test walks `core/`, `physics/` and `backends/` and fails if any module imports Qt or PyVista. One test fails if a tag number appears in a serialized scene.
- **Fixtures come from the solver's own examples** (`fem_solver/tests/data/*.geo`, `fem_solver/meshes/cap.geo`), read in place, never copied.
- **The fake solver.** `tests/backends/fake_fem.py` is a small script that honours the contract (reads `problem.json`, writes `solution.csv` and `run.json`, can be told to fail). The executable backend is tested against it. When the real `fem` gains its command-line interface, one extra test marked `@pytest.mark.real_solver` runs the capacitor through it and is skipped when the binary is absent.
- **Continuous integration** runs `pytest -m "not ui and not real_solver"` on every pull request that touches `studio/`. Run the `ui` tests locally before reporting a window milestone done.
- **Reporting.** A claim that something works in the window must say whether it was run on screen, run offscreen, or only unit-tested.

## Status

| Milestone | State | Notes |
|---|---|---|
| M0 | not started | |
| M1 | not started | |
| M2 | not started | |
| M3 | not started | |
| M4 | not started | |
| M5 | not started | |
| M6 | not started | |
| M7 | not started | |
| M8 | not started | |
| M9 | not started | |
