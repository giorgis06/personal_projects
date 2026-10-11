# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A collection of independent personal projects that share one git repository and nothing else. Each top-level folder builds and runs on its own.

- `fem_solver/`: a 2D finite element solver in C++ with a Python front end. The active project. It has its own `fem_solver/CLAUDE.md`, which adds to this file; read it before working there.
- `particle_engine/`: an SFML particle simulation with a spatial grid and Barnes-Hut gravity. Build and run from that folder with `make sim && ./sim`; it needs SFML and Eigen installed system-wide.
- `inverted_pendulum/` and `random_walk/` are local only (gitignored).

This file holds the rules that apply to the whole repository. Anything specific to one project belongs in that project's own `CLAUDE.md`, not here.

## Git rules

- `master` is protected: changes arrive only through pull requests. Never commit on `master`.
- Long-lived integration branches (currently `ui/base-branch`) are treated the same way: never commit on them directly; cut a branch from them and open a pull request back.
- Never force-push, and never rewrite commits that have been pushed.
- Build outputs, generated meshes (`*.msh`) and `compile_commands.json` stay uncommitted.

These rules are also enforced for Claude by the hooks in `.claude/hooks/` (registered in `.claude/settings.json`). If a hook blocks a command, follow its message; do not look for a way around it.

## Formatting and linting

Configuration lives at the repository root and applies to every project.

```bash
# Python (ruff.toml)
ruff check .
ruff format --check .

# C++ (.clang-format); skip vendored third-party headers
clang-format --dry-run --Werror $(git ls-files '*.cpp' '*.h' | grep -v -e doctest.h -e gmsh.h)
```

A hook runs ruff on every Python file Claude writes, so Python edits arrive already formatted.

## Continuous integration

Workflows in `.github/workflows/` run on pull requests. `lint-python.yaml` runs ruff on every pull request; the others are per project and only run when that project's files change.

## Code structure

Across all projects the owner keeps code in small files grouped into folders by meaning, one concept per file. Follow that: no catch-all modules, and split a file that starts doing two jobs.

## Reporting

State what was run and what was not. Never report a task as done while a build, test or lint command is failing; give the failing output instead.
