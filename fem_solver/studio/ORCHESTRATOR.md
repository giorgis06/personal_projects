# FEM Studio: build plan

This file is the plan of record for a Python desktop app that sits in front of the C++ finite element solver in the parent folder (`fem_solver/`). Whoever builds a milestone reads this file first, works only inside `fem_solver/studio/`, and updates the status table at the bottom when a milestone is done.

## Goal

A user can open the app, look at an existing geometry or build a new one, assign materials and boundary conditions by name, mesh it, run a solver on it, and look at the result as a 2D heatmap and as a 3D surface. Adding a second kind of problem (magnetostatics, heat, waves) or a second solver (a Python reference solver, a GPU build) later should mean adding one new folder, not editing the existing ones.

The app is a front end over one data object, the **Scene**: geometry plus physics, with names as the only link between the two. Everything the window can do, a script or notebook must also be able to do by importing the same Scene classes with no window. The solver's README describes this idea under "Idea: defining problems easily"; read that section before starting.

## What exists today

Read these before writing anything:

- `CLAUDE.md` at the repository root and `fem_solver/CLAUDE.md`: the repository's rules on git, structure and reporting. They apply to this work; where this plan is more specific, this plan wins.
- `fem_solver/README.md`: the maths, the layout, and the scene-file idea.
- `fem_solver/problem/`, `fem_solver/materials/`, `fem_solver/mesh/mesh.h`: what a problem consists of on the C++ side. A material is a symmetric 2x2 tensor per region, a boundary condition is Dirichlet, Neumann or Robin per boundary, the source is a function of (x, y).
- `fem_solver/tests/data/*.geo`: example geometries, tracked in git. Regions and boundaries are gmsh physical groups with names such as `"glass"`, `"outer"`. `two_materials.geo` is the one with two named regions and an interface.
- `fem_solver/meshes/cap.geo`: the cylindrical capacitor (inner electrode, glass shell, air, outer wall). It is the reference example for this app, but the `meshes/` folder is gitignored, so the file exists on the owner's machine only and is absent in continuous integration. Read it to learn the geometry; never make a test depend on it.
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
- Linting and formatting are configured once, in `ruff.toml` at the repository root. Do not add a `[tool.ruff]` section or a second ruff config under `studio/`: the nearest config wins, so it would silently replace the shared one. A repository hook already runs ruff on every Python file as it is written.
- Be laconic everywhere you write prose. The owner reads all of it, and every extra line costs them time.
  - **Code comments:** only for what the code cannot say itself, such as a non-obvious reason, a constraint or a unit. One line. No comment that restates the code, no banner or divider comments, no notes about what was changed.
  - **Docstrings:** one line on public classes and functions. None on private helpers or on tests whose names already say what they check.
  - **Commit messages:** one subject line of at most 72 characters. Add a body only when the reason is not obvious, and keep it to three lines.
  - **Pull request descriptions:** at most eight lines: what it adds, how it was verified, what was not verified. Do not walk through the diff file by file.
  - **Reports, summaries and status notes:** the same limit and content. No preamble, no recap of the plan, no closing offers.
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
  design/
    workbench.html           view-only reference mockup of the main window
  femstudio/
    __main__.py              python -m femstudio
    core/
      scene/                 the Scene: single source of truth
        shapes.py            Circle, Rectangle, Polygon (parametric, named)
        operations.py        union, difference, intersection
        region.py            a named area that will carry a material
        boundary.py          a named curve (outline, side or between two regions) with a condition
        scene.py             Scene = shapes + regions + boundaries + physics values
        serialization.py     Scene <-> scene.json
        validation.py        checks listed under "Validation"
        editing.py           edit operations that keep names consistent; refused edits change nothing
        history.py           undo and redo by scene snapshots, one step per committed edit
      expressions/
        grammar.py           the allowed expression language
        evaluate.py          parse, validate, evaluate on numpy arrays
      mesh/
        mesher.py            Scene -> gmsh model -> .msh, assigns tags from names
        geometry.py          shapes and booleans -> OpenCASCADE surfaces and curves
        selection.py         finds the model curves a named boundary refers to
        session.py           one gmsh session with its log, shared by mesher and reader
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
        document.py          what is open: a mesh, with the scene and project it came from
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
      main_window.py         assembles the regions below; holds no logic of its own
      session.py             what is open: edits, undo, saving, re-meshing for the preview
      theme/
        tokens.py            every colour, font and spacing value, by name
        stylesheet.py        builds the Qt stylesheet from the tokens
        zoom.py              the interface scale factor, its limits and the stored choice
      shell/
        menu_bar.py          File, Edit, View, Run, Help
        workflow_bar.py      the five step tabs, backend selector, Run button
        scene_dock.py        the Scene tree (left)
        properties_dock.py   hosts the current panel (right)
        log_dock.py          solver output (bottom)
        status_bar.py        validation summary and mesh counts
        viewport.py          the tabbed centre area that hosts the views
      panels/                geometry, physics, mesh, solve, results (one file each); shown in the Properties dock; geometry edits the scene
      views/                 geometry_view, mesh_view, heatmap_view, surface_view; one viewport tab each
      widgets/               dock_title, readouts (M5); expression_edit, tensor_edit (M7)
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
- `validate(scene)`, `write_problem(scene, mesh, folder)` and `derive(scene, mesh, solution)`, which returns the derived output fields by name (the unit constants stay in the problem type's folder)

**SolverBackend** (`backends/base.py`):

- `name`, `supported_problem_types` (`*` means any; the solver itself refuses what it lacks)
- `is_available()`: for the executable backend, whether the file exists and can be run (the contract has no probe to ask more)
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
  "source": {"rho": "(exp(-((x-1)^2 + y^2)/0.02)) / 8.8541878128e-12"},
  "boundaries": {
    "inner_electrode": {"kind": "dirichlet", "g": "5*cos(theta)"},
    "outer_wall":      {"kind": "dirichlet", "g": "0"}
  },
  "solver": {"method": "cg", "tolerance": 1e-10, "max_iterations": 10000},
  "output": "result"
}
```

- Keys under `regions` and `boundaries` are gmsh physical group names in the `.msh`. Outer edges no boundary names are listed under the reserved name `default_boundary`.
- Every value that can vary in space is an expression string. The language is fixed in `core/expressions/grammar.py`: numbers, `+ - * / ^`, parentheses, variables `x y r theta`, constant `pi`, functions `sin cos tan exp log sqrt abs`. It is deliberately the subset that small C++ expression libraries accept.

Result, written by the solver into `<run_folder>/result/`:

- `solution.csv` with header `node_tag,u`: one row per mesh node, using the gmsh node tag from the `.msh`, so no ordering assumption is shared between the two programs.
- `run.json`: `{"status", "iterations", "residual", "timings": {...}, "message"}`.

`results/reader.py` is the only module that knows this format. A `.vtu` reader can be added beside it later without touching anything else.

### Units

The file holds the numbers the solver works on, for `-div(a grad u) = f` with no units. The window works in SI, and the electrostatics writer is the only place that converts (epsilon_0 = 8.8541878128e-12 F/m, a named constant in `physics/electrostatics/`). The solver is 2D, so every quantity is per metre of depth.

| Quantity | User enters | Written to `problem.json` |
|---|---|---|
| Lengths | m | unchanged |
| `epsilon` | relative, no unit | unchanged |
| Dirichlet `g` | V | unchanged |
| `rho` | C/m^3 | `(rho) / 8.8541878128e-12` |
| Neumann `g` (surface charge) | C/m^2 | `(g) / 8.8541878128e-12` |
| Robin | `kappa` in 1/m, `u_ref` in V | `kappa` unchanged, `g = (kappa) * (u_ref)` |

Scaling is applied to the expression string in parentheses, so it stays in the expression language. Robin's file `g` is `kappa * g_D + g_N` with `g_N = 0`, as in `problem/boundary_conditions.h`; `kappa` must be positive. Outputs `u` (V) and `E` (V/m) need no conversion; energy density is `1/2 epsilon_0 epsilon_r |E|^2` in J/m^3.

## Validation

Run before meshing, shown in the window as a list with the offending name:

- every expression parses;
- every material tensor is symmetric positive definite;
- every region has a material;
- a boundary with no condition defaults to insulating (Neumann, g = 0), with a warning;
- no Dirichlet boundary at all is a warning (solution defined only up to a constant);
- names are unique and non-empty; regions and boundaries share one namespace, as in the `.msh`;
- the name `default_boundary` is reserved.

The mesher also refuses what the solver's `validate()` refuses: an outer edge no boundary names (unless `Scene.default_boundary` is set, which then covers those edges and is listed in `problem.json` under the name `default_boundary`), two boundaries naming one curve, and regions that do not form one connected piece.

## Window design: Workbench

The owner chose this design from four mockups. It is settled: build this layout and do not substitute another. `design/workbench.html` is the reference picture (open it in a browser; it is view-only and its numbers are examples). This section is the specification, and wins where the two differ.

### Regions

The main window is a `QMainWindow`. From top to bottom:

| Region | Content | Behaviour |
|---|---|---|
| Menu bar | File, Edit, View, Run, Help | View lists every dock so a closed one can be reopened |
| Workflow bar | Five step tabs in order: Geometry, Physics, Mesh, Solve, Results. On the right, the backend selector and the Run button | Choosing a step selects the matching panel in the Properties dock and the most useful viewport tab for it. It never hides the Scene dock or blocks going back to an earlier step |
| Scene dock (left) | A tree with four groups: Shapes, Regions, Boundaries, Runs. Each row is a name and a short value summary (`glass  eps 4`, `inner_electrode  5 V`, `run 3  0.41 s`) | Selecting a row shows its fields in the Properties dock and highlights it in the viewport. Selecting a run loads its result |
| Viewport (centre) | Tabs: Heatmap, 3D surface, Mesh, Geometry. Field views have a colour bar with value and unit labels on their right | The only region that stretches; docks keep their width when the window grows |
| Properties dock (right) | The panel for the current step and selection, generated from the ProblemType. On Results it holds a Display group (field, range, colour map, mesh overlay on or off) and the Probe readout | Edits apply to the Scene immediately and re-run validation |
| Log dock (bottom) | Solver and mesher output as it arrives | Monospace, read-only, scrolls to the newest line |
| Status bar | Validation summary (errors and warnings), node count, triangle count, mesh size | Clicking the validation summary opens the list of findings |

The three docks are `QDockWidget`s: movable, closable, and restored to this default arrangement by View > Reset layout.

### How the regions map to code

- One step in the workflow bar corresponds to one file in `ui/panels/`.
- One viewport tab corresponds to one file in `ui/views/`.
- Each region in the table is one file in `ui/shell/`. `main_window.py` only assembles them and connects their signals.
- Adding a problem type adds no file under `ui/`: its forms come from the ProblemType.

### Look

All visual values live in `ui/theme/tokens.py` and nowhere else. No colour, font name or pixel size is written literally in any other module; a test checks `ui/` for colour literals outside `theme/`.

| Token | Value | Used for |
|---|---|---|
| `panel` | `#eceff2` | window background, dock title strips |
| `surface` | `#ffffff` | dock bodies, workflow bar, input fields |
| `stage` | `#f7f8fa` | viewport background |
| `chrome` | `#dfe4e9` | menu bar, status bar |
| `ink` | `#1b242d` | text |
| `muted` | `#647180` | secondary text, value summaries, inactive tabs |
| `rule` | `#c9d1d9` | every border and divider, 1 px |
| `selection` | `#dbe8fb` | selected tree row |
| `accent` | `#1d5fb8` | active step, Run button, focus ring |
| `success` | `#1e7d4b` | passed checks, completed run |
| `warning` | `#a15c00` | validation warnings |
| `error` | `#b3261e` | validation errors, failed run |

- **Type:** IBM Plex Sans for the interface and IBM Plex Mono for numbers, expressions, tensor entries and the log. Do not bundle font files; when the fonts are not installed, fall back to the system interface font and the system monospace font. Base size 10 pt, dock titles 9 pt uppercase.
- **Density:** compact. Rows about 22 px high, 1 px rules instead of shadows, corner radius no larger than 4 px.
- **Colour maps:** `viridis` by default. Offer `viridis`, `inferno` and `coolwarm`, with `coolwarm` meant for fields that change sign. The colour map is data colour, separate from the interface tokens.
- **Theme:** light only for now. Because every value is a token, a dark set can be added later without touching the widgets.

### Interface zoom

The whole interface scales: text, rows, paddings, dock widths and controls. The drawing in the viewport does not (the mouse wheel zooms it).

- View menu: Zoom in (`Ctrl++`, also `Ctrl+=`), Zoom out (`Ctrl+-`), Reset zoom (`Ctrl+0`); steps of 10 %, from 70 % to 200 %. The current value is shown in the status bar.
- There is one scale factor, in `ui/theme/zoom.py`. The tokens stay the 100 % values; the stylesheet and fonts are rebuilt from them times the factor, and widgets that set sizes in code read them through `zoom.px` and refresh in an `apply_zoom` method. 1 px rules stay 1 px.
- The choice is remembered between sessions (`QSettings`).

## Milestones

Each is one pull request and ends with a stop for review.

| # | Scope | Done when |
|---|---|---|
| M0 | Scaffold: folders, `pyproject.toml` (package metadata and pytest settings only), `requirements.txt`, an empty `QMainWindow` that opens (the Workbench layout itself arrives in M5), README with run instructions, and the architecture test that forbids Qt and PyVista imports outside `ui/` | `python -m femstudio` opens a window; lint passes; `pytest -m "not ui and not real_solver"` collects and passes at least one test, so the CI job goes green |
| M1 | `core/scene`, `core/expressions`, serialization, validation, and the capacitor written as a scene in `examples/` | A scene built in code round-trips through `scene.json`; every validation rule has a passing and a failing test; no Qt import in `core/` (enforced by a test) |
| M2 | `core/mesh`: mesher, reader, quality; boundaries picked by outline, by side of a shape, or between two regions | The capacitor scene from `examples/` meshes to a `.msh` whose physical names match the scene; sides, interior curves and region interfaces mesh as named edges; every `fem_solver/tests/data/*.geo` loads into MeshData with its named regions and edges |
| M3 | `physics/`: interface, registry, electrostatics spec and `problem.json` writer | Written file matches the contract; schema covered by tests |
| M4 | `backends/`, `core/results`, `core/project` | Mock backend produces a field end to end; executable backend passes tests against a fake `fem` script covering success, failure and missing binary |
| M5 | The Workbench window from "Window design": theme tokens and stylesheet, every region in `ui/shell/`, opening a `.geo` / `.msh` / project, the Geometry and Mesh viewport tabs, regions and boundaries coloured and listed by name in the Scene dock | The capacitor opens; selecting a row in the Scene dock highlights that part; the window matches the reference mockup's arrangement; the colour-literal test passes |
| M6 | Geometry editing: add shapes from forms, boolean operations, naming, live preview, undo | The capacitor can be rebuilt from an empty scene in the window |
| M7 | Physics, mesh and solve panels generated from the ProblemType and shown in the Properties dock; validation summary in the status bar; background solve with live output in the Log dock | A full run with the mock backend from the window, window stays responsive |
| M8 | Results: the Heatmap and 3D surface viewport tabs (height = value), colour bar, and the Display group and Probe readout in the Properties dock (field selector including derived fields, range, colour map, mesh overlay) | Both views show the same run; probe value matches the field array |
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
- **Two kinds, kept apart by a marker.** Tests of `core/`, `physics/` and `backends/` need no display and carry no marker. Tests that create a window carry `@pytest.mark.ui`, use pytest-qt with `QT_QPA_PLATFORM=offscreen`, and are limited to "opens, loads the example, does not raise". Register both markers used in this plan, `ui` and `real_solver`, in `pyproject.toml`, and turn on strict marker checking so a mistyped marker fails instead of silently running.
- **What a test must check.** A real expected value, worked out independently of the code under test: a known area, a known node count for a fixed mesh size, a hand-written `problem.json`, an analytic field. A test that only checks "no exception" is acceptable for window smoke tests and nowhere else.
- **Every rule has a failing case.** Each validation rule, each backend error path (non-zero exit, missing binary, malformed result) and each expression-grammar rejection has a test that triggers it.
- **Architecture is tested too.** One test walks `core/`, `physics/` and `backends/` and fails if any module imports Qt or PyVista. One test fails if a tag number appears in a serialized scene.
- **Fixtures come from the solver's tracked examples** (`fem_solver/tests/data/*.geo`), read in place, never copied. The capacitor is rebuilt as a scene under `studio/examples/` in M1 and tests use that; nothing may read `fem_solver/meshes/`, which is not in git.
- **The fake solver.** `tests/backends/fake_fem.py` is a small script that honours the contract (reads `problem.json`, writes `solution.csv` and `run.json`, can be told to fail). The executable backend is tested against it. When the real `fem` gains its command-line interface, one extra test marked `@pytest.mark.real_solver` runs the capacitor through it and is skipped when the binary is absent.
- **Continuous integration** (`.github/workflows/studio-tests.yaml`) runs `pytest -m "not ui and not real_solver"` on every pull request that touches `studio/`, after installing `fem_solver/requirements.txt` and `studio/requirements.txt`. pytest fails when it collects no tests, so there must always be at least one unmarked test. Run the `ui` tests locally before reporting a window milestone done.
- **Reporting.** A claim that something works in the window must say whether it was run on screen, run offscreen, or only unit-tested.

## Status

| Milestone | State | Notes |
|---|---|---|
| M0 | done | Merged (#16). Launcher `run()` is in `ui/main_window.py` so `__main__.py` imports no Qt. |
| M1 | done | Merged (#17). Validation rules are generic, keyed on condition kind and tensor values, not on problem type. |
| M2 | done | Merged (#18). Unnamed outer edges are refused unless `Scene.default_boundary` is set. |
| M3 | done | Merged (#19). Units and epsilon_0 scaling per the owner decision; see Units. |
| M4 | done | Merged (#20). Run folders hold `scene.json`; stopping a solve is raising from `on_log`. |
| M5 | done | Merged (#21). Interface zoom (owner request) is in; see Window design. |
| M6 | in review | Edits are committed with Apply (one undo step each); every edit re-meshes on the window's thread for the preview. A new region gets the problem type's default material; its conditions and values come with the Physics panel (M7). |
| M7 | not started | |
| M8 | not started | |
| M9 | not started | |
