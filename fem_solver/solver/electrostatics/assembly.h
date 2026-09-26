#pragma once

#include "problem/problem.h"
#include "quadrature.h"
#include <filesystem>
#include "linalg/csr.h"

namespace fem{

    inline CSR assemble_stiffness(const PoissonProblem& problem,const TriQuadRule& tri_quad_rule){
        vector<Triplet> global_stiffness;
        for(size_t e = 0; e < problem.mesh.numElements(); ++e){
            array<array<double,2>,3> coords;
            array<int,3> element = problem.mesh.elementNodes()[e];

            for(size_t i = 0; i < element.size(); ++i){
                coords[i] = problem.mesh.nodePositions()[element[i]];
            }

            // Constant over the element: compute once, reuse for all 9 (i,j) pairs
            const array<array<double,2>,3> grads = hat_gradients(coords);
            const array<double,3>& eps = problem.materials.at(problem.mesh.elementTags()[e]).EPSILON;

            for(size_t i = 0; i < element.size(); ++i){
                for(size_t j = 0; j < element.size(); ++j){
                    // (x,y) unused while eps is constant per element, to be used them when eps(x,y) is added
                    auto a_times_grad_phi_i_dot_grad_phi_j = [&](double x, double y){
                        return dot_prod_2d(symmetric_mat_vec(eps, grads[j]), grads[i]);
                    };

                    // Global stiffness matrix gets  updated at the positions (node ids) of nodes i and j in the local frame

                    Triplet t_ij = {element[i],element[j],triangle_quadrature(tri_quad_rule, coords, a_times_grad_phi_i_dot_grad_phi_j)};                
                    global_stiffness.push_back(t_ij);
                }
            }
        }
        return to_csr(global_stiffness,problem.mesh.numNodes());
    }

} // namespace fem