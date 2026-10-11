# CLAUDE.md (fem_solver)

This file adds to the `CLAUDE.md` at the repository root. The root file's rules on git, formatting, structure and reporting apply here unchanged and are not repeated; this file covers only what is specific to the solver.

## What this project is

A 2D finite element solver written from scratch in C++17 for electrostatics, `-div(eps grad u) = rho`, with a CUDA port planned. `README.md` in this folder holds the maths, the design decisions and the roadmap; read it before changing anything.

`studio/` is a Python desktop front end for the solver, built by milestones. `studio/ORCHESTRATOR.md` is its plan of record. For work inside `studio/`, that plan overrides this file where the two differ.

## Ownership and how to help

The C++ here is the owner's hand-written learning project.

- Unless explicitly asked for a finished implementation, help by explaining and by giving skeletons with TODOs, not worked solutions.
- Do not refactor or reformat solver code as a side effect of another task.
- Work on the studio must not edit anything outside `studio/`.
- `tests/doctest.h` and `mesh/gmsh.h` are vendored third-party headers: never format, lint or edit them.

A hook asks the owner to approve every edit to the solver's C++ files and Makefile, and refuses edits to the vendored headers.

## Commands (run from `fem_solver/`)

```bash
make                      # builds ./fem
make test                 # builds and runs ./run_tests (doctest)
./run_tests -tc="cg*"     # run only test cases whose name matches
make clean
```

The build links against the gmsh shipped in the Python wheel, so the virtual environment must exist first:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

The Makefile reads headers from `.venv/include` and the library from `.venv/lib`, and creates the `libgmsh.so` symlink itself. A machine without a desktop also needs the system package `libglu1-mesa`. The `-fvisibility=hidden` flags are required, not cosmetic: without them gmsh's inline `initialize` recurses forever.

Static analysis, when wanted (config: `.clang-tidy` at the repository root):

```bash
bear -- make fem run_tests && clang-tidy -p . main.cpp mesh/mesh.cpp
```

Two workflows cover this folder: `fem_solver.yaml` runs `make test` when solver files change (skipped for draft pull requests), and `studio-tests.yaml` runs the studio's pytest suite, excluding tests marked `ui` or `real_solver`.

Generated meshes and the `meshes/` folder stay uncommitted. The fixtures in `tests/data/` are the exception and are tracked.

## Architecture

The code is almost entirely header-only inside `namespace fem`; `mesh/mesh.cpp` is the only compiled source besides `main.cpp` and the tests.

The data flow, which spans several folders:

1. `mesh/`: `load_mesh` reads a `.geo` or `.msh` through gmsh and `validate()` enforces the invariants the rest of the code assumes, most importantly counter-clockwise triangles. gmsh node tags are 1-based and are converted to 0-based in exactly one place.
2. `problem/` and `materials/`: physics is kept outside the mesh. `Materials` maps a region tag to a symmetric 2x2 tensor, `BoundaryConditions` maps an edge tag to Dirichlet, Neumann or Robin data, and `PoissonProblem` bundles them with the mesh and the source function.
3. `solver/electrostatics/assembly.h`: four independent assembly routines (stiffness, load, Robin matrix, boundary vector). Each pushes local entries as triplets, and `to_csr` in `linalg/csr.h` sums duplicates.
4. `solver/electrostatics/solver.h`: splits nodes into free and Dirichlet, builds `K_FF x_F = (b + r)_F - K_FD g`, solves it with conjugate gradient, and scatters the result back to all nodes.
5. `linalg/`: CSR storage, in-place vector operations and the preconditioned conjugate gradient.

## Constraints that are easy to break

- The conjugate gradient loop is written only against `spmv`, `dot`, `axpy` and the norm so that it maps one-to-one onto cuSPARSE and cuBLAS later. Keep it that way and keep it allocation-free.
- `double` everywhere; `float` hides convergence behaviour.
- Do not assume the number of unknowns equals the number of nodes.
- Material tensors must stay symmetric positive definite, or conjugate gradient no longer applies.
- `main.cpp` currently hardcodes one problem and has no command-line interface or result output. The interface the studio expects is specified in `studio/ORCHESTRATOR.md` under "Solver contract".

## Tests

Tests compare against answers worked out by hand: single-triangle stiffness, the patch test, exact boundary integrals, and a manufactured solution with the expected second-order convergence. New tests should do the same, and must not compare floating-point values exactly.
