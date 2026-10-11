# Kickoff prompt for the builder

Paste the text below into a new session opened at the repository root. Replace `M0` with the milestone to build.

---

You are building one milestone of FEM Studio, a Python desktop app that is the front end for a C++ finite element solver in this repository. The full plan is in `fem_solver/studio/ORCHESTRATOR.md`. Read it completely before doing anything else, then read the files it lists under "What exists today".

**Build milestone M0, and only that milestone.**

Some context the plan assumes you understand:

- The solver is the owner's personal learning project, written by hand. That is why nothing outside `fem_solver/studio/` may be edited, and why the solver has no command-line interface yet: the owner will write it against the contract in the plan. Build against the mock backend, and do not work around the missing interface by changing C++ files or by calling solver internals.
- The owner cares a great deal about structure. Their C++ is split into small files grouped by meaning, and the plan's folder layout mirrors that. Follow the layout as written. If a module you are writing wants to do two jobs, split it. If you believe the layout is wrong for something you have discovered, stop and say so instead of quietly deviating.
- The app must stay extensible to other physics and other solvers. The two interfaces in the plan (ProblemType and SolverBackend) are how. If you find yourself writing electrostatics-specific code outside `physics/electrostatics/`, or importing Qt outside `ui/`, that is a design error to fix, not a shortcut to take.
- Names, never gmsh tag numbers, connect geometry to physics.
- The look and arrangement of the window are already decided: the "Workbench" design in the plan's "Window design" section, pictured in `fem_solver/studio/design/workbench.html`. Build that. Do not propose or substitute a different layout, palette or set of fonts, and keep every visual value in the theme module as the plan says.

How to work:

1. Work on the milestone's own branch, named `ui/m0-<short-description>`. If it already exists (`ui/m0-scaffold` does, and it is where these plan files first live), switch to it; otherwise create it from an up-to-date `ui/base-branch`. The milestone lands as one pull request into `ui/base-branch`, never into `master`.
2. Use the existing virtual environment at `fem_solver/.venv`. Install new dependencies from `fem_solver/studio/requirements.txt` only, and only those listed in the plan's "Stack" section. If you think another dependency is needed, ask first.
3. Write tests alongside the code, following the plan's "Testing" section. Each "Done when" condition needs a test that would fail if the condition were not met.
4. Before you finish, run `ruff check`, `ruff format --check` and `pytest` from `fem_solver/studio/` and fix what they report.
5. Update the status table at the bottom of `ORCHESTRATOR.md`.
6. Commit, push the branch and open the pull request against `ui/base-branch`. Do not merge it.

Stop and ask the owner, instead of deciding yourself, if:

- the milestone cannot meet its "Done when" condition as written;
- you would need to change the solver contract, the folder layout or the dependency list;
- anything requires touching files outside `fem_solver/studio/` other than adding lines to `.gitignore`.

When done, report in this order: what now works and how you verified it (say explicitly whether window behaviour was run on screen, run offscreen, or only unit-tested); anything in the milestone you could not complete or verify; any decision you made that the plan did not cover; and what the next milestone will need from the owner. Keep the report short and factual.
