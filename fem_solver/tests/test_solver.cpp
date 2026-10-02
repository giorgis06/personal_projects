#include "doctest.h"
#include "solver/electrostatics/solver.h"

#include <cmath>
#include <string>

using namespace fem;

// Manufactured solution on the unit square.
//
//   u(x,y) = sin(pi x) sin(pi y) + x + 0.5 y
//
// The sine part is the interesting bit, the linear part makes the boundary values nonzero
// so g actually matters. Anisotropic, off-diagonal a, so the xy term of the tensor is exercised:
//
//       [ a11 a12 ]   [ 2   0.5 ]
//   a = [ a12 a22 ] = [ 0.5 1   ]
//
//   f = -div(a grad u) = -(a11 u_xx + 2 a12 u_xy + a22 u_yy)
//     = (a11 + a22) pi^2 sin(pi x) sin(pi y) - 2 a12 pi^2 cos(pi x) cos(pi y)
//
// One side of each BC type, so R, r and the elimination all take part:
//   bottom (1), y = 0, n = ( 0,-1)   Dirichlet   g = u
//   left   (4), x = 0, n = (-1, 0)   Dirichlet   g = u
//   right  (2), x = 1, n = ( 1, 0)   Neumann     g = n.(a grad u)
//   top    (3), y = 1, n = ( 0, 1)   Robin       g = kappa u + n.(a grad u)

namespace {

const double PI  = M_PI;
const double A11 = 2.0, A22 = 1.0, A12 = 0.5;
const double KAPPA = 3.0;

double u_exact(double x, double y){ return std::sin(PI*x)*std::sin(PI*y) + x + 0.5*y; }
double u_x(double x, double y){ return PI*std::cos(PI*x)*std::sin(PI*y) + 1.0; }
double u_y(double x, double y){ return PI*std::sin(PI*x)*std::cos(PI*y) + 0.5; }

// n.(a grad u) for an axis-aligned normal (nx, ny)
double flux(double x, double y, double nx, double ny){
    double ax = A11*u_x(x,y) + A12*u_y(x,y);
    double ay = A12*u_x(x,y) + A22*u_y(x,y);
    return nx*ax + ny*ay;
}

PoissonProblem manufactured_problem(const std::string& geo){
    Materials materials;
    materials[10] = {{A11, A22, A12}, {}, {}};

    auto f = [](double x, double y){
        return (A11 + A22)*PI*PI*std::sin(PI*x)*std::sin(PI*y) - 2.0*A12*PI*PI*std::cos(PI*x)*std::cos(PI*y);
    };

    BoundaryConditions bcs;
    bcs[1] = {BCType::Dirichlet, u_exact, {}};
    bcs[4] = {BCType::Dirichlet, u_exact, {}};
    bcs[2] = {BCType::Neumann, [](double x, double y){ return flux(x,y,1,0); }, {}};
    bcs[3] = {BCType::Robin,
              [](double x, double y){ return KAPPA*u_exact(x,y) + flux(x,y,0,1); },
              [](double, double){ return KAPPA; }};

    return PoissonProblem{load_mesh(geo), materials, f, bcs};
}

// L2 error ||u_h - u||, integrated element by element with DEGREE_2.
// L2 is what the theory promises O(h^2) in; the max nodal error is noisier on unstructured meshes.
double l2_error(const std::string& geo){
    PoissonProblem problem = manufactured_problem(geo);
    vector<double> solution;
    solve_statics_problem(problem, solution, {}, DEGREE_2, GAUSS_2, 10000, 1e-12);
    REQUIRE(solution.size() == problem.mesh.numNodes());

    double err2 = 0.0;
    for(size_t e = 0; e < problem.mesh.numElements(); ++e){
        const array<int,3>& el = problem.mesh.elementNodes()[e];
        array<array<double,2>,3> coords;
        for(int i = 0; i < 3; ++i) coords[i] = problem.mesh.nodePositions()[el[i]];
        const auto grads = hat_gradients(coords);

        err2 += triangle_quadrature(DEGREE_2, coords, [&](double x, double y){
            const array<double,3> phi = hat_values(coords, grads, x, y);
            double u_h = 0.0;
            for(int i = 0; i < 3; ++i) u_h += solution[el[i]] * phi[i];
            double d = u_h - u_exact(x, y);
            return d*d;
        });
    }
    return std::sqrt(err2);
}

} // namespace

TEST_CASE("solver: Dirichlet nodes hold g_D exactly"){
    PoissonProblem problem = manufactured_problem(TEST_DATA_DIR "square.geo");
    vector<double> solution;
    solve_statics_problem(problem, solution, {}, DEGREE_2, GAUSS_2, 10000, 1e-12);

    for(size_t i = 0; i < solution.size(); ++i){
        const auto& p = problem.mesh.nodePositions()[i];
        if(p[0] == 0.0 || p[1] == 0.0) CHECK(solution[i] == doctest::Approx(u_exact(p[0], p[1])).epsilon(1e-14));
    }
}

TEST_CASE("solver: linear u is reproduced exactly with every BC type"){
    // P1 elements contain linear functions, so u = 1 + x + 0.5 y must come out exact (up to CG tolerance).
    // f = 0, flux is constant. Catches sign or scaling bugs in R, r and the elimination.
    auto u_lin = [](double x, double y){ return 1.0 + x + 0.5*y; };
    const double ax = A11*1.0 + A12*0.5, ay = A12*1.0 + A22*0.5;   // a grad u

    Materials materials;
    materials[10] = {{A11, A22, A12}, {}, {}};
    BoundaryConditions bcs;
    bcs[1] = {BCType::Dirichlet, u_lin, {}};
    bcs[4] = {BCType::Dirichlet, u_lin, {}};
    bcs[2] = {BCType::Neumann, [ax](double, double){ return ax; }, {}};
    bcs[3] = {BCType::Robin, [=](double x, double y){ return KAPPA*u_lin(x,y) + ay; }, [](double, double){ return KAPPA; }};

    PoissonProblem problem{load_mesh(TEST_DATA_DIR "square_h0125.geo"), materials, [](double, double){ return 0.0; }, bcs};
    vector<double> solution;
    solve_statics_problem(problem, solution, {}, DEGREE_2, GAUSS_2, 10000, 1e-13);

    for(size_t i = 0; i < solution.size(); ++i){
        const auto& p = problem.mesh.nodePositions()[i];
        CHECK(std::abs(solution[i] - u_lin(p[0], p[1])) < 1e-10);
    }
}

TEST_CASE("solver: manufactured solution, L2 error falls ~4x per halving of h"){
    double e1 = l2_error(TEST_DATA_DIR "square.geo");          // h = 0.25
    double e2 = l2_error(TEST_DATA_DIR "square_h0125.geo");    // h = 0.125
    double e3 = l2_error(TEST_DATA_DIR "square_h00625.geo");   // h = 0.0625
    double e4 = l2_error(TEST_DATA_DIR "square_h003125.geo");  // h = 0.03125

    MESSAGE("L2 error: " << e1 << ", " << e2 << ", " << e3 << ", " << e4
            << "  ratios: " << e1/e2 << ", " << e2/e3 << ", " << e3/e4);

    CHECK(e4 < 1e-3);
    // O(h^2) means ratio 4; unstructured meshes don't halve h exactly, so allow some slack
    CHECK(e1/e2 > 3.5);
    CHECK(e2/e3 > 3.5);
    CHECK(e3/e4 > 3.5);
}
