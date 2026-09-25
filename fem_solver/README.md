# 2D FEM Solver — Study Plan & Project Notes

A from-scratch finite element solver for 2D geometries, in C++ with a CUDA path.
Written by hand, deliberately. This file is the map: what to read, what to learn,
and what order to build in.

**Target application: electrostatics** — `-div(eps grad phi) = rho`. That is the
Poisson problem with a per-region coefficient, so it stays real-valued and SPD
and CG works on it. Everything not specific to statics is kept general enough to
extend later (see Decisions below).

## Current state

| | |
|---|---|
| Python venv | done — numpy, scipy, matplotlib, meshio, gmsh, pytest |
| `mesh.h` | done — `Mesh` container, validated as a module (c++17/20/nvcc, multi-TU) |
| **next** | `load_msh()`, `make_unit_square()`, `validate()` |

Nothing is committed yet beyond this scaffolding. No solver exists.

## Decisions locked in

Changing these later is expensive, so they are settled:

- **`double` everywhere** for coordinates and field values. `float` runs out of
  precision during a convergence study and makes correct code look broken.
- **Counter-clockwise winding**, enforced by `validate()`, not by the parser.
  Costs no storage — it only constrains the order of the three node indices.
  Lets consumers use `det J` directly and makes outward normals well defined.
- **Boundary stored as tagged edges**, not tagged nodes. Dirichlet constrains a
  node, Neumann integrates along a segment; a node list cannot express the
  second. Edges + physical tags + a name->id map.
- **Physics lives outside `Mesh`.** `Mesh` holds geometry, topology and tag ids
  only. `BoundaryConditions` maps tag -> condition, `Materials` maps
  tag -> (eps, mu, sigma). One loaded mesh can then serve several problems,
  which is exactly what a convergence sweep needs.
- **Per-element region tags** (`Element_Tags`), because in EM the objects in the
  domain are subdomains with different material properties, not holes.
- **Never assume `numDofs() == numNodes()`.** True for P1 today; false for P2,
  for vector-valued problems, and for edge elements. Route assembly through a
  DOF indirection so those drop in without surgery.

## Ground rules

I write the code. I reach for help only when genuinely stuck — and "stuck" means
*I've formed a hypothesis and tested it and it didn't explain the behaviour*, not
*this is taking a while*.

A corollary worth writing down: *being slow is not being stuck.* The first
correct assembly routine takes most people days. That is the normal cost of
the thing, not evidence of a problem.

**When I do ask, ask well.** "My convergence rate is 1.0 when it should be 2.0,
here's my quadrature routine" is a good question. "It doesn't work" throws away
the debugging I already did.

## The honest shape of this project

The theory is a few pages. The implementation is mostly *bookkeeping* — index
mapping, boundary bookkeeping, sparse storage. Most bugs are off-by-one and
orientation errors, not misunderstood mathematics.

Budget accordingly: expect to spend more time on indices than on integrals.
That is not a sign of doing it wrong.

---

## Phase plan

Each phase ends with something runnable and *verified*. Don't start the next
until the current one is checked. Resist the urge to write the whole pipeline
before running any of it.

### Phase 0 — Theory, no code
Understand the weak form. Be able to derive, on paper, why
−∇²u = f becomes ∫∇u·∇v = ∫fv, and what happened to the boundary term.

**Done when:** I can explain integration by parts and why the boundary term
vanishes for Dirichlet conditions — without notes.

### Phase 1 — Hardcoded mesh, no file I/O
Structured triangulation of the unit square, generated in code (split each
grid cell into 2 triangles). P1 elements. Dense `K` is fine here — keep it
small (< 100 nodes) so it can be printed and stared at.

**Done when:** Dirichlet Poisson on the unit square matches an analytic solution.

### Phase 2 — Sparse + CG
Replace dense `K` with CSR. Write conjugate gradient by hand.

**Done when:** identical answers to Phase 1, and it handles ~10⁵ DOF.

### Phase 3 — Real mesh I/O
Write the `.msh` reader. Write the `.vtu` writer. Now arbitrary 2D geometry
works, and results are viewable in ParaView.

**Done when:** an L-shaped domain from gmsh solves and renders.

### Phase 3.5 — Make it electrostatics
Per-element `eps` via `Element_Tags` + a `Materials` lookup. The assembly loop
barely changes: one coefficient multiplying the local matrix.

**Write the local matrix as `K_e = A * B^T eps B`** from the start, with `eps` a
2x2 and `eps = eps_scalar * I` for isotropic materials. `B` is the 2x3 of P1
basis gradients. Anisotropic materials then cost nothing later: the table stores
3 doubles per tag (symmetric) instead of 1, and nothing else changes. `Mesh` is
untouched either way, since tags map to whatever you like. Caveats if you go
there: `eps` must stay symmetric positive definite, or CG no longer applies
(non-symmetric `eps`, e.g. magnetized plasma, needs BiCGSTAB/GMRES); `D = eps E`
in post-processing becomes a matrix-vector product; and `eps` varying *inside*
an element would need real quadrature, while constant-per-region stays exact.

Two things specific to EM that arrive here:
- **The mesh must conform to material interfaces** — element edges lie *along*
  the boundary between two `eps` regions, never across it. gmsh does this if the
  subdomains are separate surfaces sharing a curve.
- **Space is unbounded; the mesh is not.** Truncate at an artificial outer
  boundary with `phi = 0` far away. That boundary is a modelling choice, not
  physics, and carries its own tag. (Wave problems would need a PML instead.)

**Done when:** a two-dielectric problem shows the expected field discontinuity
at the interface.

### Phase 4 — GPU
Port CG: cuSPARSE for SpMV, cuBLAS for the dot/axpy. Then try matrix-free.

**Done when:** GPU result matches CPU to solver tolerance, with a real speedup.

### Later, in no particular order
Neumann BCs · P2 elements · preconditioning (Jacobi, then IC(0)) · adaptive
refinement · 2D magnetostatics (also Poisson-like, scalar `A_z`).

**Well past the horizon**, and noted only so the design does not preclude it:
time-harmonic / full-wave is complex-valued and *indefinite*, so CG stops
working (GMRES or BiCGSTAB instead), and vector wave problems need edge
(Nedelec) elements rather than nodal ones or they produce spurious modes. The
complex scalar type would belong to the field and matrix — mesh coordinates
stay real.

---

## Theory: what to read

**Start here — it's the closest match to this project:**

- **Larson & Bengzon, *The Finite Element Method: Theory, Implementation, and
  Applications*** (Springer). Chapters 1–4. This is the one. It does 2D
  triangles concretely, with actual algorithms rather than pure functional
  analysis, and its structure maps almost 1:1 onto the phase plan above.

**For conjugate gradient — read this before writing the solver:**

- **Shewchuk, *An Introduction to the Conjugate Gradient Method Without the
  Agonizing Pain*** — free, ~60 pages, genuinely the best explanation of CG
  that exists. Builds up from steepest descent with pictures.
  <https://www.cs.cmu.edu/~quake-papers/painless-conjugate-gradient.pdf>
  Read §1–8 before Phase 2; the rest when preconditioning comes up.

**Reference, not cover-to-cover:**

- **Hughes, *The Finite Element Method: Linear Static and Dynamic FEA***
  (Dover — cheap). The classic engineering treatment. Good on isoparametric
  mapping and quadrature.
- **Saad, *Iterative Methods for Sparse Linear Systems*, 2nd ed.** — free PDF
  from the author. The standard reference on Krylov methods and
  preconditioning. <https://www-users.cse.umn.edu/~saad/IterMethBook_2ndEd.pdf>
- **Strang, MIT 18.085 *Computational Science and Engineering I*** — free
  video lectures; strong on the "why" and on the structure of stiffness
  matrices. <https://ocw.mit.edu/courses/18-085-computational-science-and-engineering-i-fall-2008/>
- **Barrett et al., *Templates for the Solution of Linear Systems*** — free;
  terse pseudocode for CG and friends, good for cross-checking an
  implementation. <https://netlib.org/linalg/html_templates/Templates.html>

**For weak forms specifically**, the FEniCS/DOLFINx tutorial is a good
conceptual read even though we're not using it — it's unusually clear about
the translation from strong to weak form.
<https://jsdokken.com/dolfinx-tutorial/>

**For the electrostatics phase:** Jin, *The Finite Element Method in
Electromagnetics* — the standard reference for FEM applied to EM specifically.
Worth having once Phase 3.5 starts; not needed before.

**For the GPU phase (Phase 4, not before):** Cecka, Lew & Darve, *"Assembly of
finite element methods on graphics processors"* (IJNME, 2011) — the canonical
comparison of coloring vs. atomics vs. matrix-free assembly. Search the title.

> Links checked 2026-09-20. If one has drifted, search the title — all of these
> are stable, well-known works.

---

## The specific theory checklist

Things to genuinely understand, not just recognise:

- [ ] **Strong vs. weak form.** Why weaken? (Lower the differentiability
      requirement on `u` — allows piecewise-linear solutions that aren't twice
      differentiable.)
- [ ] **Integration by parts in 2D** (the divergence theorem / Green's
      identity) — where the boundary integral comes from and when it vanishes.
- [ ] **Test vs. trial functions.** Why Galerkin picks them from the same space.
- [ ] **Basis (shape) functions.** P1 hat functions on triangles: each is 1 at
      its own node, 0 at all others, linear in between. Sketch one by hand.
- [ ] **Barycentric / area coordinates.** The natural coordinate system on a
      triangle; makes the P1 gradients constant and easy.
- [ ] **The reference element and the affine map.** Compute on one canonical
      triangle, map to each physical one. The Jacobian determinant is the area
      scale factor — and its *sign* encodes orientation (see traps below).
- [ ] **Quadrature.** Gauss rules on triangles. For P1 Poisson the integrand is
      constant so 1-point is exact — know *why*, so it's clear when it stops
      being enough.
- [ ] **The element stiffness matrix `K_e`.** 3×3 for P1. Should come out
      symmetric, singular (rank 2), with rows summing to zero. Good check.
- [ ] **Assembly / the scatter operation.** Local index (0,1,2) → global node
      index. The heart of the bookkeeping.
- [ ] **Boundary conditions.** Dirichlet (constrain the value — *how* matters,
      see traps) vs. Neumann (a boundary integral in the load vector — it falls
      out naturally; nothing to constrain).
- [ ] **Properties of `K`.** Symmetric positive definite *after* BCs applied,
      sparse (~7 nonzeros/row), and *singular before* them. This is exactly why
      CG is the right solver.
- [ ] **Convergence rates.** P1 in the L² norm should be O(h²). This is the
      single most valuable test — see Validation.

---

## Libraries: what to actually know

### Right now
| What | Why | Depth needed |
|---|---|---|
| **C++ STL** | `vector`, `array`, `span`. Contiguous storage is the whole game. | Working fluency |
| **CMake** | Builds the C++/CUDA mix. | Just enough — one `CMakeLists.txt` |
| **gmsh** (Python API) | Generating meshes. | The `.geo` concepts + the ~10 API calls |
| **numpy / scipy** | The validation oracle. `scipy.sparse`, `spsolve`, `cg`. | Working fluency |
| **matplotlib** | `tricontourf`, `tripcolor` for quick looks. | Two functions |

### Phase 3+
| What | Why |
|---|---|
| **meshio** | Cross-check my `.msh` parser and `.vtu` writer against a known-good one |
| **ParaView** | Actually viewing results. Learn: warp-by-scalar, contour, the spreadsheet view |

### Phase 4
| What | Why |
|---|---|
| **CUDA C++** | Kernels, memory model, occupancy |
| **cuSPARSE** | Sparse matrix-vector product in CSR. <https://docs.nvidia.com/cuda/cusparse/> |
| **cuBLAS** | Level-1 only: `Ddot`, `Daxpy`, `Dnrm2`. <https://docs.nvidia.com/cuda/cublas/> |

Note the RTX 5070 is Blackwell → compile with `-arch=sm_120`.

### Reference only — do NOT build on these
- **Eigen** (already installed, header-only) — use as an *oracle*:
  `SparseMatrix` + `SimplicialLDLT` gives a trustworthy answer to compare
  against. Using its solver as *my* solver defeats the project.
  <https://eigen.tuxfamily.org/dox/>
- **SuiteSparse / CHOLMOD** — for a serious CPU baseline, much later.

**Deliberately not using:** deal.II, FEniCS, MFEM. They're excellent and they
would do the entire project for me. Worth reading, not linking against.

---

## Mesh & file formats: what to learn

### The data structure
Two parallel arrays, **not** a vector of self-contained triangles:

```cpp
std::vector<std::array<double,2>> nodes;  // coordinates
std::vector<std::array<int,3>>    tris;   // INDICES into nodes
```

Interior nodes are shared by ~6 triangles. The shared node *identity* is what
assembly is built on — global DOF number = node index. Duplicating coordinates
per-triangle destroys exactly the information the method needs.

Also worth building eventually: **node → element adjacency** (which triangles
touch node `i`). Needed for race-free GPU assembly and for error estimation.

### The formats
| Ext | What | Direction | Text format |
|---|---|---|---|
| `.geo` | gmsh's geometry scripting DSL | input to gmsh | plain text, **not** XML |
| `.msh` | gmsh's mesh output | **my program reads this** | plain text sections |
| `.vtu` | VTK unstructured grid | **my program writes this** | XML |

Pipeline: `.geo` → [gmsh] → `.msh` → [my solver] → `.vtu` → [ParaView]

### `.msh` — read the spec
<https://gmsh.info/doc/texinfo/gmsh.html#MSH-file-format>

**Write the parser against format 2.2, not 4.1.** Ask gmsh for it:
```python
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
```
2.2 is a flat list — `tag type numTags tags... nodes...`, one element per line.
4.1 nests everything in entity blocks. Same information, far more parsing.

Learn these:
- [ ] Section structure: `$Nodes`, `$Elements`, `$PhysicalNames`
- [ ] **Element type codes**: `1`=2-node line, `2`=3-node triangle,
      `4`=4-node tet, `9`=6-node (P2) triangle, `15`=point
- [ ] **A `.msh` holds mixed-dimension elements.** A meshed unit square gave
      198 "elements": 4 corner points + 32 boundary lines + 162 triangles.
      Filter to type 2 for the domain — and the type-1 lines *are the boundary*,
      which is how to find Dirichlet nodes without geometric guessing.
- [ ] **Physical groups.** Tag curves/surfaces in the `.geo`
      (`Physical Curve("wall") = {...}`). Two reasons this is mandatory: if
      *any* physical group is defined, gmsh exports **only** tagged entities —
      untagged geometry silently disappears; and the tags are how a boundary
      gets labelled Dirichlet vs. Neumann.
- [ ] Coordinates are always 3 components. In 2D, z ≡ 0. Don't assume 2 floats.

### `.vtu` — write the writer
<https://examples.vtk.org/site/VTKFileFormats/>
XML, ~40 lines to emit. Needs `Points`, `Cells` (connectivity + offsets +
types — triangle is VTK type **5**), and `PointData` for the solution field.
Start with ASCII; base64/binary only if files get painful.

---

## Validation — the most important section

Debugging a solver by staring at plots does not work. Two techniques make this
tractable, and skipping them is how projects like this die:

**1. Compare against scipy at every stage.** Dump `K` and `f` from C++, load in
Python, `scipy.sparse.linalg.spsolve`. If scipy's answer differs from my CG,
the *solver* is broken. If scipy's answer is also wrong, *assembly* is broken.
This one bisection separates the two failure modes instantly — it's worth
building the dump/load plumbing early, and it pays for itself many times over.

**2. Method of Manufactured Solutions (MMS).** Pick a solution first, e.g.
`u = sin(πx)sin(πy)`. Push it through the PDE analytically to get the `f` that
produces it. Solve with that `f`; compare against the known `u`.

Then **refine the mesh and check the convergence *rate***, not just the error:
halving `h` should cut the L² error by ~4× for P1 (O(h²)). Make this a pytest.

A wrong rate is a precise diagnostic, not a vague "it's off":
- **Rate ≈ 1 instead of 2** → usually quadrature, or Dirichlet BCs applied in a
  way that breaks symmetry
- **Rate ≈ 2 but error plateaus** → CG tolerance too loose; the solver error is
  now dominating the discretisation error
- **No convergence at all** → assembly or connectivity

---

## Traps worth knowing in advance

These are the standard ones. Each has cost someone a full day:

- **1-based vs. 0-based.** gmsh node tags start at 1. C++ starts at 0. Subtract
  one, in exactly one place, and write down where.
- **Triangle orientation.** A negative Jacobian determinant means the nodes are
  wound clockwise. Use `abs()` for the area, *or* enforce CCW winding at load
  time — but know which, because it silently flips signs otherwise.
- **Dirichlet BCs destroying symmetry.** Zeroing a row of `K` but not the
  matching column makes `K` non-symmetric — and CG then fails or stalls, since
  it *requires* SPD. Zero both and move the known values to the RHS; or use the
  large-diagonal-penalty trick, understanding its conditioning cost.
- **Forgetting `K` is singular before BCs.** Pure Neumann Poisson has a
  null space (constants) — the solution is unique only up to an additive
  constant.
- **CSR built with duplicate entries.** The same (i,j) appears from multiple
  elements. They must be *summed*, not overwritten. Classic silent wrong answer.
- **Assembling into a structure that reallocates.** Build the sparsity pattern
  first (symbolic pass), then fill values (numeric pass). Don't grow a map
  inside the hot loop.
- **Comparing floats exactly** in tests. Use a tolerance tied to `h`.

---

## Environment

```bash
source .venv/bin/activate     # numpy, scipy, matplotlib, meshio, gmsh, pytest
```

C++ side still needs: `sudo apt install cmake ninja-build`

`mesh.h` is header-only and has no dependencies beyond the STL. It compiles
clean under c++17 and c++20 with `-Wall -Wextra -Wpedantic -Wshadow
-Wconversion -Wold-style-cast`, links across translation units, and builds
under `nvcc -arch=sm_120`.

Already present: gcc 11.4, CUDA 13.3 (cuBLAS/cuSPARSE/cuSOLVER),
Eigen 3.4 at `/usr/include/eigen3`.

---

## Glossary

Terms that appear constantly in the literature and are rarely defined in-line:

- **DOF** — degree of freedom. One unknown. For P1 scalar problems: one per node.
- **`h`** — characteristic mesh size (typical element diameter). Convergence
  rates are always stated in powers of `h`.
- **Stiffness matrix `K`** — the system matrix. Name is inherited from
  structural mechanics; it applies to any PDE.
- **Load vector `f`** — the RHS. Same etymology.
- **SPD** — symmetric positive definite. CG's precondition for working at all.
- **SpMV** — sparse matrix-vector product. The dominant cost in CG.
- **CSR** — compressed sparse row. Three arrays: `values`, `col_indices`,
  `row_ptr`.
- **P1 / P2** — piecewise polynomial degree 1 / 2 on each element.
- **Isoparametric** — using the same basis functions for geometry and solution.
- **Galerkin** — test space = trial space.
- **MMS** — method of manufactured solutions.
