#include "doctest.h"
#include "linalg/conjugate_gradient.h"

using namespace fem;

// Dense helper: max |x_i - y_i|
static double max_diff(const vector<double> &x, const vector<double> &y) {
  double m = 0.0;
  for (size_t i = 0; i < x.size(); ++i)
    m = std::max(m, std::abs(x[i] - y[i]));
  return m;
}

//     [ 4  1  0 ]
// A = [ 1  3  1 ]    SPD, uneven diagonal so Jacobi actually does something
//     [ 0  1  2 ]
static CSR spd_3x3() {
  return to_csr({{0, 0, 4},
                 {0, 1, 1},
                 {1, 0, 1},
                 {1, 1, 3},
                 {1, 2, 1},
                 {2, 1, 1},
                 {2, 2, 2}},
                3);
}

// 1D Laplacian tridiag(-1, 2, -1), n x n
static CSR laplacian_1d(int n) {
  vector<Triplet> t;
  for (int i = 0; i < n; ++i) {
    t.push_back({i, i, 2.0});
    if (i > 0)
      t.push_back({i, i - 1, -1.0});
    if (i < n - 1)
      t.push_back({i, i + 1, -1.0});
  }
  return to_csr(t, n);
}

TEST_CASE("xpby: y = x + b y") {
  vector<double> x = {1, 2, 3};
  vector<double> y = {10, 20, 30};
  xpby(0.5, x, y);
  CHECK(y == vector<double>{6, 12, 18});

  xpby(0.0, x, y); // b = 0 copies x
  CHECK(y == x);

  vector<double> short_y = {1, 2};
  CHECK_THROWS(xpby(1.0, x, short_y));
}

TEST_CASE("zeros and norm2") {
  CHECK(zeros(3) == vector<double>{0, 0, 0});
  CHECK(norm2({3, 4}) == doctest::Approx(5));
}

TEST_CASE(
    "inverse_diagonal: 1/A_ii, throws on zero, negative or missing diagonal") {
  vector<double> d = inverse_diagonal(spd_3x3());
  CHECK(d[0] == doctest::Approx(0.25));
  CHECK(d[1] == doctest::Approx(1.0 / 3));
  CHECK(d[2] == doctest::Approx(0.5));

  CHECK_THROWS(
      inverse_diagonal(to_csr({{0, 0, 1}, {1, 1, 0}}, 2))); // stored zero
  CHECK_THROWS(
      inverse_diagonal(to_csr({{0, 0, 1}, {1, 1, -2}}, 2))); // negative
  CHECK_THROWS(inverse_diagonal(
      to_csr({{0, 0, 1}, {1, 0, 1}}, 2))); // row 1 has no diagonal
}

TEST_CASE(
    "cg: 3x3 SPD converges to the known solution in at most 3 iterations") {
  CSR A = spd_3x3();
  vector<double> x_true = {1, -2, 3};
  vector<double> b(3);
  spmv(A, x_true, b);

  vector<double> x = conjugate_gradient_solve(A, b, zeros(3), 1e-12, 3);
  CHECK(max_diff(x, x_true) < 1e-10);
}

TEST_CASE("cg: 1D Laplacian, n = 50") {
  const int n = 50;
  CSR A = laplacian_1d(n);
  vector<double> x_true(n);
  for (int i = 0; i < n; ++i)
    x_true[i] = std::sin(0.1 * i) + 0.01 * i;
  vector<double> b(n);
  spmv(A, x_true, b);

  vector<double> x = conjugate_gradient_solve(A, b, zeros(n), 1e-12, 2 * n);
  CHECK(max_diff(x, x_true) < 1e-8);

  // residual check independent of x_true
  vector<double> Ax(n);
  spmv(A, x, Ax);
  axpy(-1.0, b, Ax);
  CHECK(norm2(Ax) <= 1e-12 * norm2(b) * 10);
}

TEST_CASE("cg: exact initial guess returns it untouched") {
  CSR A = spd_3x3();
  vector<double> x_true = {1, -2, 3};
  vector<double> b(3);
  spmv(A, x_true, b);

  CHECK(conjugate_gradient_solve(A, b, x_true, 1e-12, 3) == x_true);
}

TEST_CASE("cg: b = 0 gives x = 0 without dividing by zero") {
  vector<double> x =
      conjugate_gradient_solve(spd_3x3(), zeros(3), zeros(3), 1e-12, 3);
  CHECK(x == zeros(3));
}

TEST_CASE("cg: empty initial guess means start from zeros, still solves") {
  CSR A = spd_3x3();
  vector<double> x_true = {1, -2, 3};
  vector<double> b(3);
  spmv(A, x_true, b);

  vector<double> x = conjugate_gradient_solve(A, b, {}, 1e-12, 3);
  CHECK(max_diff(x, x_true) < 1e-10);
}

TEST_CASE("cg: too few iterations throws") {
  const int n = 50;
  CSR A = laplacian_1d(n);
  vector<double> b(n, 1.0);
  CHECK_THROWS(conjugate_gradient_solve(A, b, zeros(n), 1e-12, 2));
}
