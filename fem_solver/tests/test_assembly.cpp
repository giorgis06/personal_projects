#include "doctest.h"
#include "solver/electrostatics/assembly.h"

#include <cmath>
#include <numeric>
#include <set>

using namespace fem;
using doctest::Approx;

// ---- helpers ---------------------------------------------------------------

static double entry(const CSR& K, int r, int c){
    for(int k = K.row_ptr[r]; k < K.row_ptr[r+1]; ++k){
        if(K.col_idx[k] == c) return K.values[k];
    }
    return 0.0;
}

static vector<double> spmv(const CSR& K, const vector<double>& x){
    vector<double> y(K.n, 0.0);
    for(int r = 0; r < K.n; ++r){
        for(int k = K.row_ptr[r]; k < K.row_ptr[r+1]; ++k){
            y[r] += K.values[k] * x[K.col_idx[k]];
        }
    }
    return y;
}

// Nodes on the outer boundary: those on an edge owned by exactly one triangle.
// Computed from the elements, so tagged interface edges don't count.
static std::set<int> boundary_nodes(const Mesh& mesh){
    map<pair<int,int>,int> owners;
    for(const auto& e : mesh.elementNodes()){
        for(int v = 0; v < 3; ++v){
            int a = e[v], b = e[(v+1)%3];
            if(a > b) std::swap(a,b);
            ++owners[{a,b}];
        }
    }
    std::set<int> nodes;
    for(const auto& [edge, count] : owners){
        if(count == 1){ nodes.insert(edge.first); nodes.insert(edge.second); }
    }
    return nodes;
}

static CSR single_triangle_K(array<double,3> eps){
    // Unit right triangle (0,0),(1,0),(0,1), region tag 10. Bypasses validate():
    // the triangle is already CCW and valid.
    Mesh mesh({{0,0},{1,0},{0,1}}, {{0,1,2}}, {10});
    PoissonProblem p{std::move(mesh), {{10, {eps, {}, {}}}}, nullptr, {}};
    return assemble_stiffness(p, CENTROID);
}

// ---- single element, checked by hand ----------------------------------------
// ∇φ0 = (-1,-1), ∇φ1 = (1,0), ∇φ2 = (0,1), area 1/2.  K_ij = area * ∇φ_iᵀ ε ∇φ_j

TEST_CASE("assembly: single triangle, eps = I"){
    CSR K = single_triangle_K({1,1,0});
    const double expected[3][3] = {{ 1.0, -0.5, -0.5},
                                   {-0.5,  0.5,  0.0},
                                   {-0.5,  0.0,  0.5}};
    for(int i = 0; i < 3; ++i)
        for(int j = 0; j < 3; ++j)
            CHECK(entry(K,i,j) == Approx(expected[i][j]));
}

TEST_CASE("assembly: single triangle, eps scales linearly"){
    CSR K1 = single_triangle_K({1,1,0});
    CSR K2 = single_triangle_K({2,2,0});
    for(int i = 0; i < 3; ++i)
        for(int j = 0; j < 3; ++j)
            CHECK(entry(K2,i,j) == Approx(2 * entry(K1,i,j)));
}

TEST_CASE("assembly: single triangle, anisotropic eps = diag(1,4)"){
    CSR K = single_triangle_K({1,4,0});
    const double expected[3][3] = {{ 2.5, -0.5, -2.0},
                                   {-0.5,  0.5,  0.0},
                                   {-2.0,  0.0,  2.0}};
    for(int i = 0; i < 3; ++i)
        for(int j = 0; j < 3; ++j)
            CHECK(entry(K,i,j) == Approx(expected[i][j]));
}

TEST_CASE("assembly: single triangle, off-diagonal eps_xy"){
    // eps = [[1, 0.5],[0.5, 1]] adds area * 0.5 * (gx_i gy_j + gy_i gx_j) to the eps = I result
    CSR K = single_triangle_K({1,1,0.5});
    CHECK(entry(K,0,0) == Approx(1.0 + 0.5*0.5*2));   // 1.5
    CHECK(entry(K,1,2) == Approx(0.0 + 0.5*0.5*1));   // 0.25
    CHECK(entry(K,2,1) == Approx(entry(K,1,2)));
}

// ---- assembled on real meshes ------------------------------------------------

static void check_structure(const CSR& K, size_t num_nodes){
    REQUIRE(K.n == static_cast<int>(num_nodes));
    REQUIRE(K.row_ptr.size() == num_nodes + 1);

    for(int r = 0; r < K.n; ++r){
        double row_sum = 0.0;
        for(int k = K.row_ptr[r]; k < K.row_ptr[r+1]; ++k){
            const int c = K.col_idx[k];
            row_sum += K.values[k];
            CHECK(K.values[k] == entry(K, c, r));          // exact symmetry
        }
        CHECK(std::abs(row_sum) < 1e-12);                   // constants are in the null space
        CHECK(entry(K, r, r) > 0);                          // positive diagonal
    }
}

TEST_CASE("assembly: unit square, structure"){
    Mesh mesh = load_mesh("tests/data/square.geo");
    const size_t n = mesh.numNodes();
    PoissonProblem p{std::move(mesh), {{10, {{1,1,0}, {}, {}}}}, nullptr, {}};
    check_structure(assemble_stiffness(p, CENTROID), n);
}

TEST_CASE("assembly: two materials, structure"){
    Mesh mesh = load_mesh("tests/data/two_materials.geo");
    const size_t n = mesh.numNodes();
    PoissonProblem p{std::move(mesh), {{10, {{4,4,0}, {}, {}}}, {11, {{1,1,0}, {}, {}}}}, nullptr, {}};
    check_structure(assemble_stiffness(p, CENTROID), n);
}

// ---- load vector -------------------------------------------------------------

// Degree-2 rule (points at (2/3,1/6,1/6) and permutations, equal weights):
// exact for quadratics, which f·φ_i is when f is linear.

static double dot(const vector<double>& a, const vector<double>& b){
    double s = 0.0;
    for(size_t i = 0; i < a.size(); ++i) s += a[i] * b[i];
    return s;
}

TEST_CASE("load: single triangle, f = 1 gives area/3 per node"){
    Mesh mesh({{0,0},{1,0},{0,1}}, {{0,1,2}}, {10});
    PoissonProblem p{std::move(mesh), {{10, {{1,1,0}, {}, {}}}}, [](double, double){ return 1.0; }, {}};
    vector<double> b = assemble_load(p, CENTROID);

    REQUIRE(b.size() == 3);
    for(double bi : b) CHECK(bi == Approx(0.5 / 3));
}

TEST_CASE("load: f = 1 sums to the total area"){
    // The φ_i sum to 1 everywhere, so Σ b_i = ∫ f
    auto ones = [](double, double){ return 1.0; };

    PoissonProblem square{load_mesh("tests/data/square.geo"), {{10, {{1,1,0}, {}, {}}}}, ones, {}};
    vector<double> b = assemble_load(square, CENTROID);
    CHECK(b.size() == square.mesh.numNodes());
    CHECK(std::accumulate(b.begin(), b.end(), 0.0) == Approx(1.0));

    PoissonProblem two{load_mesh("tests/data/two_materials.geo"),
                       {{10, {{4,4,0}, {}, {}}}, {11, {{1,1,0}, {}, {}}}}, ones, {}};
    b = assemble_load(two, CENTROID);
    CHECK(std::accumulate(b.begin(), b.end(), 0.0) == Approx(2.0));
}

TEST_CASE("load: f = x tested against u = y gives the integral of x*y"){
    // For any nodal vector u, b·u = Σ_i u_i ∫ f φ_i = ∫ f · (Σ_i u_i φ_i).
    // With u_i = y_i the sum Σ u_i φ_i reproduces y exactly (P1 is exact for linears),
    // so b·u = ∫_[0,1]² x y = 1/4. This weights every entry of b by its node's y,
    // so a single misplaced or mis-scaled entry shows up, unlike a plain sum.
    Mesh mesh = load_mesh("tests/data/square.geo");
    const auto positions = mesh.nodePositions();
    PoissonProblem p{std::move(mesh), {{10, {{1,1,0}, {}, {}}}}, [](double x, double){ return x; }, {}};

    vector<double> u(positions.size());
    for(size_t i = 0; i < u.size(); ++i) u[i] = positions[i][1];

    // x·φ_i is quadratic, so the degree-2 rule makes this exact
    CHECK(dot(assemble_load(p, DEGREE_2), u) == Approx(0.25).epsilon(1e-12));

    // The centroid rule is only exact for linears: close, but not exact
    const double centroid = dot(assemble_load(p, CENTROID), u);
    CHECK(centroid == Approx(0.25).epsilon(1e-2));
}

TEST_CASE("assembly: patch test, K u = 0 at interior nodes for linear u"){
    // P1 elements reproduce linear functions exactly, and a linear u satisfies
    // -div(eps grad u) = 0 for any constant eps. So every interior row of K u
    // must vanish; only boundary rows carry flux.
    Mesh mesh = load_mesh("tests/data/square.geo");
    const std::set<int> boundary = boundary_nodes(mesh);
    const auto positions = mesh.nodePositions();

    for(array<double,3> eps : {array<double,3>{1,1,0}, array<double,3>{1,4,0.5}}){
        CAPTURE(eps[0]); CAPTURE(eps[1]); CAPTURE(eps[2]);

        PoissonProblem p{Mesh(mesh), {{10, {eps, {}, {}}}}, nullptr, {}};
        CSR K = assemble_stiffness(p, CENTROID);

        vector<double> u(K.n);
        for(int i = 0; i < K.n; ++i) u[i] = 2.0 + 3.0*positions[i][0] - 1.5*positions[i][1];

        vector<double> Ku = spmv(K, u);
        REQUIRE(boundary.size() < static_cast<size_t>(K.n));   // there are interior nodes
        for(int i = 0; i < K.n; ++i){
            if(boundary.count(i)) continue;
            CHECK(std::abs(Ku[i]) < 1e-12);
        }
    }
}