#pragma once

#include "assembly.h"
#include "conjugate_gradient.h"

// Solves -div(a grad u) = f with Dirichlet / Neumann / Robin boundary edges.
//
// Split the nodes into free (F) and Dirichlet (D), u_h = sum_F ξ_j phi_j +
// sum_D g_j phi_j, and test only with the free phi_i. With K = A + R:
//
//      K_FF ξ_F = (b + r)_F - K_FD g
//
//   A   stiffness            int a grad phi_j . grad phi_i
//   R   Robin matrix         int_E kappa phi_i phi_j    (Robin edges)
//   b   load vector          int f phi_i
//   r   boundary vector      int_E g phi_i              (Neumann / Robin edges)
//   g   Dirichlet values     g_D at the D nodes (interpolated, not integrated)
//
// The full solution is ξ_F on the free nodes and g on the Dirichlet ones.

namespace fem {

enum class Solvers { CG, CHOLESKY };

inline void solve_statics_problem(const PoissonProblem &problem,
                                  vector<double> &solution,
                                  const vector<double> &initial_guess,
                                  const TriQuadRule &tri_quad_rule,
                                  const EdgeQuadRule &edge_quad_rule,
                                  int max_iterations,
                                  double tolerance = 1e-10) {
  // Assemble over all nodes. Nothing here knows which nodes are Dirichlet yet.
  // Matrix: K = A + R. Vector: b + r.
  CSR A = assemble_stiffness(problem, tri_quad_rule);
  CSR R = assemble_R(problem, edge_quad_rule);
  CSR K = add_csr(A, R);
  vector<double> b = assemble_load(problem, tri_quad_rule);
  vector<double> r = assemble_r(problem, edge_quad_rule);
  vector<double> b_plus_r = b;
  axpy(1.0, r, b_plus_r);

  // Node split. g2f / g2d map a global node id to its free / Dirichlet id (-1
  // if it isn't one). Every node is exactly one of the two, Dirichlet wins at
  // corners.
  array<vector<int>, 2> gen2free_dir = general2free_dirichlet(problem);
  const vector<int> &g2f = gen2free_dir[0];
  int num_free = number_of_free_nodes(g2f);
  const vector<int> &g2d = gen2free_dir[1];
  int num_dir = A.n - num_free;

  // Known part of the solution: g_D at every Dirichlet node, in Dirichlet
  // numbering.
  vector<double> g = assemble_g(problem, g2d, num_dir);

  // Right-hand side pieces, all in free numbering (size num_free):
  //   K_FD g     = (K u_D)_F, how the known boundary values push on the free
  //   nodes (b + r)_F  = only the free rows, since we only test with free phi_i
  vector<double> k_fd_g = assemble_K_fd_times_g(K, g2f, g2d, g, num_free);
  vector<double> b_plus_r_f = assemble_b_plus_r_f(b_plus_r, g2f, num_free);

  // System matrix: the free-free block of K. SPD, so CG applies.
  CSR K_ff = assemble_K_ff(K, g2f, num_free);

  // K_FF ξ_F = (b + r)_F - K_FD g
  const CSR &rhs = K_ff;
  vector<double> lhs = b_plus_r_f;
  axpy(-1.0, k_fd_g, lhs);

  // Solve for the free values only
  vector<double> free_solution = conjugate_gradient_solve(
      rhs, lhs, initial_guess, tolerance, max_iterations);

  solution = assemble_full_solution(free_solution, g, g2f, g2d);
}

} // namespace fem
