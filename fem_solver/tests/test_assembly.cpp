#include "doctest.h"
#include "solver/electrostatics/assembly.h"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <set>

using namespace fem;
using doctest::Approx;

// ---- helpers ---------------------------------------------------------------

static double entry(const CSR &K, int r, int c) {
  for (int k = K.row_ptr[r]; k < K.row_ptr[r + 1]; ++k) {
    if (K.col_idx[k] == c)
      return K.values[k];
  }
  return 0.0;
}

// Nodes on the outer boundary: those on an edge owned by exactly one triangle.
// Computed from the elements, so tagged interface edges don't count.
static std::set<int> boundary_nodes(const Mesh &mesh) {
  map<pair<int, int>, int> owners;
  for (const auto &e : mesh.elementNodes()) {
    for (int v = 0; v < 3; ++v) {
      int a = e[v], b = e[(v + 1) % 3];
      if (a > b)
        std::swap(a, b);
      ++owners[{a, b}];
    }
  }
  std::set<int> nodes;
  for (const auto &[edge, count] : owners) {
    if (count == 1) {
      nodes.insert(edge.first);
      nodes.insert(edge.second);
    }
  }
  return nodes;
}

static CSR single_triangle_K(array<double, 3> eps) {
  // Unit right triangle (0,0),(1,0),(0,1), region tag 10. Bypasses validate():
  // the triangle is already CCW and valid.
  Mesh mesh({{0, 0}, {1, 0}, {0, 1}}, {{0, 1, 2}}, {10});
  PoissonProblem p{std::move(mesh), {{10, {eps, {}, {}}}}, nullptr, {}};
  return assemble_stiffness(p, CENTROID);
}

// ---- single element, checked by hand ----------------------------------------
// ∇φ0 = (-1,-1), ∇φ1 = (1,0), ∇φ2 = (0,1), area 1/2.  K_ij = area * ∇φ_iᵀ ε
// ∇φ_j

TEST_CASE("assembly: single triangle, eps = I") {
  CSR K = single_triangle_K({1, 1, 0});
  const double expected[3][3] = {
      {1.0, -0.5, -0.5}, {-0.5, 0.5, 0.0}, {-0.5, 0.0, 0.5}};
  for (int i = 0; i < 3; ++i)
    for (int j = 0; j < 3; ++j)
      CHECK(entry(K, i, j) == Approx(expected[i][j]));
}

TEST_CASE("assembly: single triangle, eps scales linearly") {
  CSR K1 = single_triangle_K({1, 1, 0});
  CSR K2 = single_triangle_K({2, 2, 0});
  for (int i = 0; i < 3; ++i)
    for (int j = 0; j < 3; ++j)
      CHECK(entry(K2, i, j) == Approx(2 * entry(K1, i, j)));
}

TEST_CASE("assembly: single triangle, anisotropic eps = diag(1,4)") {
  CSR K = single_triangle_K({1, 4, 0});
  const double expected[3][3] = {
      {2.5, -0.5, -2.0}, {-0.5, 0.5, 0.0}, {-2.0, 0.0, 2.0}};
  for (int i = 0; i < 3; ++i)
    for (int j = 0; j < 3; ++j)
      CHECK(entry(K, i, j) == Approx(expected[i][j]));
}

TEST_CASE("assembly: single triangle, off-diagonal eps_xy") {
  // eps = [[1, 0.5],[0.5, 1]] adds area * 0.5 * (gx_i gy_j + gy_i gx_j) to the
  // eps = I result
  CSR K = single_triangle_K({1, 1, 0.5});
  CHECK(entry(K, 0, 0) == Approx(1.0 + 0.5 * 0.5 * 2)); // 1.5
  CHECK(entry(K, 1, 2) == Approx(0.0 + 0.5 * 0.5 * 1)); // 0.25
  CHECK(entry(K, 2, 1) == Approx(entry(K, 1, 2)));
}

// ---- assembled on real meshes
// ------------------------------------------------

static void check_structure(const CSR &K, size_t num_nodes) {
  REQUIRE(K.n == static_cast<int>(num_nodes));
  REQUIRE(K.row_ptr.size() == num_nodes + 1);

  for (int r = 0; r < K.n; ++r) {
    double row_sum = 0.0;
    for (int k = K.row_ptr[r]; k < K.row_ptr[r + 1]; ++k) {
      const int c = K.col_idx[k];
      row_sum += K.values[k];
      CHECK(K.values[k] == entry(K, c, r)); // exact symmetry
    }
    CHECK(std::abs(row_sum) < 1e-12); // constants are in the null space
    CHECK(entry(K, r, r) > 0);        // positive diagonal
  }
}

TEST_CASE("assembly: unit square, structure") {
  Mesh mesh = load_mesh(TEST_DATA_DIR "square.geo");
  const size_t n = mesh.numNodes();
  PoissonProblem p{std::move(mesh), {{10, {{1, 1, 0}, {}, {}}}}, nullptr, {}};
  check_structure(assemble_stiffness(p, CENTROID), n);
}

TEST_CASE("assembly: two materials, structure") {
  Mesh mesh = load_mesh(TEST_DATA_DIR "two_materials.geo");
  const size_t n = mesh.numNodes();
  PoissonProblem p{std::move(mesh),
                   {{10, {{4, 4, 0}, {}, {}}}, {11, {{1, 1, 0}, {}, {}}}},
                   nullptr,
                   {}};
  check_structure(assemble_stiffness(p, CENTROID), n);
}

// ---- load vector
// -------------------------------------------------------------

// Degree-2 rule (points at (2/3,1/6,1/6) and permutations, equal weights):
// exact for quadratics, which f·φ_i is when f is linear.

TEST_CASE("load: single triangle, f = 1 gives area/3 per node") {
  Mesh mesh({{0, 0}, {1, 0}, {0, 1}}, {{0, 1, 2}}, {10});
  PoissonProblem p{std::move(mesh),
                   {{10, {{1, 1, 0}, {}, {}}}},
                   [](double, double) { return 1.0; },
                   {}};
  vector<double> b = assemble_load(p, CENTROID);

  REQUIRE(b.size() == 3);
  for (double bi : b)
    CHECK(bi == Approx(0.5 / 3));
}

TEST_CASE("load: f = 1 sums to the total area") {
  // The φ_i sum to 1 everywhere, so Σ b_i = ∫ f
  auto ones = [](double, double) { return 1.0; };

  PoissonProblem square{load_mesh(TEST_DATA_DIR "square.geo"),
                        {{10, {{1, 1, 0}, {}, {}}}},
                        ones,
                        {}};
  vector<double> b = assemble_load(square, CENTROID);
  CHECK(b.size() == square.mesh.numNodes());
  CHECK(std::accumulate(b.begin(), b.end(), 0.0) == Approx(1.0));

  PoissonProblem two{load_mesh(TEST_DATA_DIR "two_materials.geo"),
                     {{10, {{4, 4, 0}, {}, {}}}, {11, {{1, 1, 0}, {}, {}}}},
                     ones,
                     {}};
  b = assemble_load(two, CENTROID);
  CHECK(std::accumulate(b.begin(), b.end(), 0.0) == Approx(2.0));
}

TEST_CASE("load: f = x tested against u = y gives the integral of x*y") {
  // For any nodal vector u, b·u = Σ_i u_i ∫ f φ_i = ∫ f · (Σ_i u_i φ_i).
  // With u_i = y_i the sum Σ u_i φ_i reproduces y exactly (P1 is exact for
  // linears), so b·u = ∫_[0,1]² x y = 1/4. This weights every entry of b by its
  // node's y, so a single misplaced or mis-scaled entry shows up, unlike a
  // plain sum.
  Mesh mesh = load_mesh(TEST_DATA_DIR "square.geo");
  const auto positions = mesh.nodePositions();
  PoissonProblem p{std::move(mesh),
                   {{10, {{1, 1, 0}, {}, {}}}},
                   [](double x, double) { return x; },
                   {}};

  vector<double> u(positions.size());
  for (size_t i = 0; i < u.size(); ++i)
    u[i] = positions[i][1];

  // x·φ_i is quadratic, so the degree-2 rule makes this exact
  CHECK(dot(assemble_load(p, DEGREE_2), u) == Approx(0.25).epsilon(1e-12));

  // The centroid rule is only exact for linears: close, but not exact
  const double centroid = dot(assemble_load(p, CENTROID), u);
  CHECK(centroid == Approx(0.25).epsilon(1e-2));
}

TEST_CASE("assembly: patch test, K u = 0 at interior nodes for linear u") {
  // P1 elements reproduce linear functions exactly, and a linear u satisfies
  // -div(eps grad u) = 0 for any constant eps. So every interior row of K u
  // must vanish; only boundary rows carry flux.
  Mesh mesh = load_mesh(TEST_DATA_DIR "square.geo");
  const std::set<int> boundary = boundary_nodes(mesh);
  const auto positions = mesh.nodePositions();

  for (array<double, 3> eps :
       {array<double, 3>{1, 1, 0}, array<double, 3>{1, 4, 0.5}}) {
    CAPTURE(eps[0]);
    CAPTURE(eps[1]);
    CAPTURE(eps[2]);

    PoissonProblem p{Mesh(mesh), {{10, {eps, {}, {}}}}, nullptr, {}};
    CSR K = assemble_stiffness(p, CENTROID);

    vector<double> u(K.n);
    for (int i = 0; i < K.n; ++i)
      u[i] = 2.0 + 3.0 * positions[i][0] - 1.5 * positions[i][1];

    vector<double> Ku(K.n);
    spmv(K, u, Ku);
    REQUIRE(boundary.size() <
            static_cast<size_t>(K.n)); // there are interior nodes
    for (int i = 0; i < K.n; ++i) {
      if (boundary.count(i))
        continue;
      CHECK(std::abs(Ku[i]) < 1e-12);
    }
  }
}
// ---- Robin boundary matrix
// ----------------------------------------------------- R_ij = ∫_E κ φ_i φ_j
// over Robin edges only. φ_i φ_j is quadratic along an edge, so these use
// GAUSS_2 (exact up to cubics).

static BoundaryCondition robin(std::function<double(double, double)> kappa) {
  return {BCType::Robin, [](double, double) { return 0.0; }, std::move(kappa)};
}

TEST_CASE("R: single edge, constant kappa gives kappa*L/6*[[2,1],[1,2]]") {
  // Edge (0,0)-(3,4), length 5, kappa = 2
  Mesh mesh({{0, 0}, {3, 4}, {0, 4}}, {{0, 1, 2}}, {10}, {{0, 1}}, {1});
  PoissonProblem p{std::move(mesh),
                   {{10, {{1, 1, 0}, {}, {}}}},
                   nullptr,
                   {{1, robin([](double, double) { return 2.0; })}}};
  CSR R = assemble_R(p, GAUSS_2);

  const double c = 2.0 * 5.0 / 6.0;
  CHECK(entry(R, 0, 0) == Approx(2 * c));
  CHECK(entry(R, 1, 1) == Approx(2 * c));
  CHECK(entry(R, 0, 1) == Approx(c));
  CHECK(entry(R, 1, 0) == Approx(c));
  CHECK(entry(R, 2, 2) == 0.0);
}

TEST_CASE("R: linear kappa = x on the unit edge") {
  // ∫_0^1 x(1-x)² = 1/12,  ∫ x²(1-x) = 1/12,  ∫ x³ = 1/4
  Mesh mesh({{0, 0}, {1, 0}, {0, 1}}, {{0, 1, 2}}, {10}, {{0, 1}}, {1});
  PoissonProblem p{std::move(mesh),
                   {{10, {{1, 1, 0}, {}, {}}}},
                   nullptr,
                   {{1, robin([](double x, double) { return x; })}}};
  CSR R = assemble_R(p, GAUSS_2);

  CHECK(entry(R, 0, 0) == Approx(1.0 / 12));
  CHECK(entry(R, 0, 1) == Approx(1.0 / 12));
  CHECK(entry(R, 1, 0) == Approx(1.0 / 12));
  CHECK(entry(R, 1, 1) == Approx(1.0 / 4));
}

TEST_CASE("R: Dirichlet and Neumann edges contribute nothing") {
  // Only edge 0-1 is Robin; the others carry no kappa and must be skipped, not
  // called
  Mesh mesh({{0, 0}, {1, 0}, {0, 1}}, {{0, 1, 2}}, {10},
            {{0, 1}, {1, 2}, {2, 0}}, {1, 2, 3});
  auto zero = [](double, double) { return 0.0; };
  PoissonProblem p{std::move(mesh),
                   {{10, {{1, 1, 0}, {}, {}}}},
                   nullptr,
                   {{1, robin([](double, double) { return 1.0; })},
                    {2, {BCType::Dirichlet, zero, {}}},
                    {3, {BCType::Neumann, zero, {}}}}};
  CSR R = assemble_R(p, GAUSS_2);

  CHECK(entry(R, 0, 0) == Approx(1.0 / 3));
  CHECK(entry(R, 0, 1) == Approx(1.0 / 6));
  CHECK(entry(R, 2, 2) == 0.0);
  CHECK(entry(R, 1, 2) == 0.0);
  CHECK(entry(R, 0, 2) == 0.0);
}

TEST_CASE("R: all-Robin unit square, 1ᵀR1 = perimeter and yᵀRy = ∫ y² ds") {
  // Σφ_i = 1, so 1ᵀR1 = ∫_∂Ω κ = 4 for κ = 1.
  // With u_i = y_i, uᵀRu = ∫_∂Ω y² = 0 (bottom) + 1/3 (right) + 1 (top) + 1/3
  // (left) = 5/3.
  Mesh mesh = load_mesh(TEST_DATA_DIR "square.geo");
  const auto positions = mesh.nodePositions();
  auto one = [](double, double) { return 1.0; };
  PoissonProblem p{
      std::move(mesh),
      {{10, {{1, 1, 0}, {}, {}}}},
      nullptr,
      {{1, robin(one)}, {2, robin(one)}, {3, robin(one)}, {4, robin(one)}}};
  CSR R = assemble_R(p, GAUSS_2);

  const vector<double> ones(R.n, 1.0);
  vector<double> y(R.n);
  for (int i = 0; i < R.n; ++i)
    y[i] = positions[i][1];

  vector<double> Rx(R.n);
  spmv(R, ones, Rx);
  CHECK(dot(Rx, ones) == Approx(4.0));
  spmv(R, y, Rx);
  CHECK(dot(Rx, y) == Approx(5.0 / 3));

  for (int r = 0; r < R.n; ++r)
    for (int k = R.row_ptr[r]; k < R.row_ptr[r + 1]; ++k)
      CHECK(R.values[k] == entry(R, R.col_idx[k], r));
}

// ---- boundary load vector
// ------------------------------------------------------ r_i = ∫_E g φ_i over
// Neumann and Robin edges (g = g_N, or κ g_D + g_N). Dirichlet edges are
// handled by elimination, so they must not contribute here.

TEST_CASE("r: single Neumann edge, g = 1 gives L/2 per node") {
  // Edge uses nodes 1 and 2 (not 0 and 1), so a local/global index mix-up shows
  Mesh mesh({{0, 0}, {3, 0}, {3, 4}}, {{0, 1, 2}}, {10}, {{1, 2}}, {1});
  PoissonProblem p{
      std::move(mesh),
      {{10, {{1, 1, 0}, {}, {}}}},
      nullptr,
      {{1, {BCType::Neumann, [](double, double) { return 1.0; }, {}}}}};
  vector<double> r = assemble_r(p, GAUSS_2);

  REQUIRE(r.size() == 3);
  CHECK(r[0] == 0.0);
  CHECK(r[1] == Approx(2.0));
  CHECK(r[2] == Approx(2.0));
}

TEST_CASE("r: linear g = x on a diagonal edge") {
  // Edge node1 (1,0) -> node2 (0,1), L = √2, x = 1 - t:
  // r_1 = L ∫(1-t)² = L/3,  r_2 = L ∫(1-t)t = L/6
  Mesh mesh({{0, 0}, {1, 0}, {0, 1}}, {{0, 1, 2}}, {10}, {{1, 2}}, {1});
  PoissonProblem p{
      std::move(mesh),
      {{10, {{1, 1, 0}, {}, {}}}},
      nullptr,
      {{1, {BCType::Neumann, [](double x, double) { return x; }, {}}}}};
  vector<double> r = assemble_r(p, GAUSS_2);

  const double L = std::sqrt(2.0);
  CHECK(r[0] == 0.0);
  CHECK(r[1] == Approx(L / 3));
  CHECK(r[2] == Approx(L / 6));
}

TEST_CASE("r: Robin edges count, Dirichlet edges do not") {
  // Edges 0-1 Robin, 1-2 Dirichlet, 2-0 Neumann, all with g = 1.
  // Node 0 gets 1/2 from each unit leg; node 1 only from 0-1; node 2 only from
  // 2-0.
  Mesh mesh({{0, 0}, {1, 0}, {0, 1}}, {{0, 1, 2}}, {10},
            {{0, 1}, {1, 2}, {2, 0}}, {1, 2, 3});
  auto one = [](double, double) { return 1.0; };
  PoissonProblem p{std::move(mesh),
                   {{10, {{1, 1, 0}, {}, {}}}},
                   nullptr,
                   {{1, {BCType::Robin, one, one}},
                    {2, {BCType::Dirichlet, one, {}}},
                    {3, {BCType::Neumann, one, {}}}}};
  vector<double> r = assemble_r(p, GAUSS_2);

  CHECK(r[0] == Approx(1.0));
  CHECK(r[1] == Approx(0.5));
  CHECK(r[2] == Approx(0.5));
}

TEST_CASE("r: all-Neumann unit square, Σr = perimeter and r·y = ∫ x y ds") {
  // Σφ_i = 1, so Σr = ∫_∂Ω 1 = 4.
  // With u_i = y_i, r·u = ∫_∂Ω x y = 0 (bottom) + 1/2 (right) + 1/2 (top) + 0
  // (left) = 1. The mesh has more triangles than boundary edges, so looping
  // over the wrong count shows.
  Mesh mesh = load_mesh(TEST_DATA_DIR "square.geo");
  const auto positions = mesh.nodePositions();
  REQUIRE(mesh.numElements() != mesh.numEdges());

  BoundaryCondition one{
      BCType::Neumann, [](double, double) { return 1.0; }, {}};
  BoundaryCondition xg{BCType::Neumann, [](double x, double) { return x; }, {}};

  PoissonProblem p1{Mesh(mesh),
                    {{10, {{1, 1, 0}, {}, {}}}},
                    nullptr,
                    {{1, one}, {2, one}, {3, one}, {4, one}}};
  vector<double> r = assemble_r(p1, GAUSS_2);
  REQUIRE(r.size() == mesh.numNodes());
  CHECK(std::accumulate(r.begin(), r.end(), 0.0) == Approx(4.0));

  PoissonProblem p2{Mesh(mesh),
                    {{10, {{1, 1, 0}, {}, {}}}},
                    nullptr,
                    {{1, xg}, {2, xg}, {3, xg}, {4, xg}}};
  vector<double> y(mesh.numNodes());
  for (size_t i = 0; i < y.size(); ++i)
    y[i] = positions[i][1];
  CHECK(dot(assemble_r(p2, GAUSS_2), y) == Approx(1.0));
}

// ---- Dirichlet / free node split
// ---------------------------------------------

TEST_CASE(
    "node split: every node gets exactly one role, Dirichlet wins at corners") {
  // Left side (tag 4) Dirichlet, the rest Neumann. The interior is untagged.
  Mesh mesh = load_mesh(TEST_DATA_DIR "square.geo");
  const auto positions = mesh.nodePositions();
  auto zero = [](double, double) { return 0.0; };
  PoissonProblem p{std::move(mesh),
                   {{10, {{1, 1, 0}, {}, {}}}},
                   nullptr,
                   {{1, {BCType::Neumann, zero, {}}},
                    {2, {BCType::Neumann, zero, {}}},
                    {3, {BCType::Neumann, zero, {}}},
                    {4, {BCType::Dirichlet, zero, {}}}}};

  auto [g2f, g2d] = general2free_dirichlet(p);
  const size_t n = p.mesh.numNodes();
  REQUIRE(g2f.size() == n);
  REQUIRE(g2d.size() == n);

  std::set<int> free_ids, dir_ids;
  for (size_t i = 0; i < n; ++i) {
    CAPTURE(i);
    CHECK(((g2f[i] >= 0) != (g2d[i] >= 0))); // exactly one role
    if (g2f[i] >= 0)
      free_ids.insert(g2f[i]);
    if (g2d[i] >= 0)
      dir_ids.insert(g2d[i]);

    const bool on_left = std::abs(positions[i][0]) < 1e-12;
    CHECK((g2d[i] >= 0) == on_left); // Dirichlet iff on x = 0
  }

  // Indices are 0..count-1 with no gaps or repeats
  const size_t nF =
      std::count_if(g2f.begin(), g2f.end(), [](int v) { return v >= 0; });
  const size_t nD =
      std::count_if(g2d.begin(), g2d.end(), [](int v) { return v >= 0; });
  CHECK(nF + nD == n);
  CHECK(free_ids.size() == nF);
  CHECK(dir_ids.size() == nD);
  CHECK(*free_ids.rbegin() == static_cast<int>(nF) - 1);
  CHECK(*dir_ids.rbegin() == static_cast<int>(nD) - 1);
}

TEST_CASE("node split: tags without a BC are skipped, no BCs means all free") {
  // Edge tag 7 has no entry in bcs, e.g. a material interface
  Mesh mesh({{0, 0}, {1, 0}, {0, 1}}, {{0, 1, 2}}, {10}, {{0, 1}}, {7});
  PoissonProblem p{std::move(mesh), {{10, {{1, 1, 0}, {}, {}}}}, nullptr, {}};

  auto [g2f, g2d] = general2free_dirichlet(p);
  CHECK(g2f == vector<int>{0, 1, 2});
  CHECK(g2d == vector<int>{-1, -1, -1});
}

// ---- Dirichlet elimination pieces
// ----------------------------------------------
//     [ 1  2  0  3 ]
// M = [ 2  4  5  0 ]    F = {0, 2},  D = {1, 3}
//     [ 0  5  6  7 ]
//     [ 3  0  7  8 ]

static CSR four_by_four_M() {
  return to_csr({{0, 0, 1},
                 {0, 1, 2},
                 {0, 3, 3},
                 {1, 0, 2},
                 {1, 1, 4},
                 {1, 2, 5},
                 {2, 1, 5},
                 {2, 2, 6},
                 {2, 3, 7},
                 {3, 0, 3},
                 {3, 2, 7},
                 {3, 3, 8}},
                4);
}

TEST_CASE("elimination: K_FF, K_FD g and (b+r)_F on a hand example") {
  const CSR M = four_by_four_M();
  const vector<int> g2f = {0, -1, 1, -1};
  const vector<int> g2d = {-1, 0, -1, 1};

  //  K_FF = [ 1  0 ]
  //         [ 0  6 ]
  CSR Kff = assemble_K_ff(M, g2f, 2);
  CHECK(Kff.n == 2);
  CHECK(Kff.values == vector<double>{1, 6});
  CHECK(Kff.col_idx == vector<int>{0, 1});

  // g = 2 at node 1, 3 at node 3:  row 0: 2*2 + 3*3 = 13,  row 2: 5*2 + 7*3 =
  // 31
  CHECK(assemble_K_fd_times_g(M, g2f, g2d, {2, 3}, 2) ==
        vector<double>{13, 31});

  CHECK(assemble_b_plus_r_f({10, 11, 12, 13}, g2f, 2) ==
        vector<double>{10, 12});
}

TEST_CASE("assemble_g: g_D evaluated at every Dirichlet node") {
  // Left (tag 4) and top (tag 3) Dirichlet with the same linear g, so the
  // shared corner (0,1) is unambiguous
  Mesh mesh = load_mesh(TEST_DATA_DIR "square.geo");
  const auto positions = mesh.nodePositions();
  auto g_D = [](double x, double y) { return 2.0 + 3.0 * x - y; };
  auto zero = [](double, double) { return 0.0; };
  PoissonProblem p{std::move(mesh),
                   {{10, {{1, 1, 0}, {}, {}}}},
                   nullptr,
                   {{1, {BCType::Neumann, zero, {}}},
                    {2, {BCType::Neumann, zero, {}}},
                    {3, {BCType::Dirichlet, g_D, {}}},
                    {4, {BCType::Dirichlet, g_D, {}}}}};

  auto [g2f, g2d] = general2free_dirichlet(p);
  const int nD = static_cast<int>(
      std::count_if(g2d.begin(), g2d.end(), [](int v) { return v >= 0; }));
  REQUIRE(nD > 0);

  // g_D >= 1 on the left and top sides, so a leftover 0 means an entry was
  // never set
  vector<double> g = assemble_g(p, g2d, nD);
  REQUIRE(g.size() == static_cast<size_t>(nD));
  for (double v : g)
    CHECK(v >= 1.0);

  for (size_t n = 0; n < g2d.size(); ++n) {
    if (g2d[n] < 0)
      continue;
    CAPTURE(n);
    CHECK(g[g2d[n]] == Approx(g_D(positions[n][0], positions[n][1])));
  }
}

TEST_CASE("assemble_g: no Dirichlet edges gives an empty vector") {
  Mesh mesh({{0, 0}, {1, 0}, {0, 1}}, {{0, 1, 2}}, {10}, {{0, 1}}, {1});
  PoissonProblem p{
      std::move(mesh),
      {{10, {{1, 1, 0}, {}, {}}}},
      nullptr,
      {{1, {BCType::Neumann, [](double, double) { return 1.0; }, {}}}}};
  auto [g2f, g2d] = general2free_dirichlet(p);
  CHECK(assemble_g(p, g2d, 0).empty());
}
