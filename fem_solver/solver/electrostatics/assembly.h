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

    inline CSR assemble_R(const PoissonProblem& problem, const EdgeQuadRule& edge_quad_rule){
        vector<Triplet> R;
        for(size_t e = 0; e < problem.mesh.numEdges(); ++e){
            array<array<double,2>,2> coords;
            array<int,2> edge = problem.mesh.edgeNodes()[e];
            int edge_tag = problem.mesh.edgeTags()[e];

            for(size_t i = 0; i < edge.size(); ++i){ // Get coordinates of edge nodes
                coords[i] = problem.mesh.nodePositions()[edge[i]];
            } 
            
            const auto& bc = problem.bcs.at(edge_tag); // ONLY ROBIN CONDITIONS GET KAPPA
            for(size_t i = 0; i < edge.size(); ++i){ // Iterate over possible combinations of edge nodes
                for(size_t j = 0; j < edge.size(); ++j){
                    if(bc.type == BCType::Robin){
                        auto k_times_phi_i_times_phi_j = [&](double x,double y, double t){
                            auto phi = hat_values_on_edge(t);
                            return bc.kappa(x,y) * phi[i] * phi[j]; // kappa * phi_i * phi_j   
                        };
                        Triplet R_ij = {edge[i],edge[j],edge_quadrature(edge_quad_rule,coords,k_times_phi_i_times_phi_j)};
                        R.push_back(R_ij);
                    }
                    else{
                        continue;
                    }
                }
            }            
        }
        
        return to_csr(std::move(R),problem.mesh.numNodes());
    }

    inline vector<double> assemble_load(const PoissonProblem& problem, const TriQuadRule& tri_quad_rule){
        vector<double> load_vector(problem.mesh.numNodes(),0.0);

        for(size_t e = 0; e < problem.mesh.numElements(); ++e){
            array<array<double,2>,3> coords;
            array<int,3> element = problem.mesh.elementNodes()[e];

            for(size_t i = 0; i < element.size(); ++i){
                coords[i] = problem.mesh.nodePositions()[element[i]];
            }

            const auto grads = hat_gradients(coords); 

            for(size_t i = 0; i < element.size(); ++i){
                auto f_times_phi_i = [&](double x,double y){
                    const array<double,3> hat_value = hat_values(coords,grads,x,y);
                    return problem.f(x,y) * hat_value[i];
                };

                // b_i += b(loc2glb(i) == element[i]) over element e;

                load_vector[element[i]] += triangle_quadrature(tri_quad_rule,coords,f_times_phi_i);
            }
        }
        return load_vector;
    }

    inline vector<double> assemble_r(const PoissonProblem& problem, const EdgeQuadRule& edge_quad_rule){
        vector<double> r(problem.mesh.numNodes(),0.0);
        
        for(size_t e = 0; e < problem.mesh.numEdges(); ++e){
            array<array<double,2>,2> coords;
            array<int,2> edge = problem.mesh.edgeNodes()[e];
            int edge_tag = problem.mesh.edgeTags()[e];

            for(size_t i = 0; i < edge.size(); ++i){
                coords[i] = problem.mesh.nodePositions()[edge[i]];
            }

            const auto& bc = problem.bcs.at(edge_tag);
            for(size_t i = 0; i < edge.size(); ++i){
                if(bc.type != BCType::Dirichlet){
                    auto g_times_phi_i = [&](double x, double y, double t){
                        auto phi = hat_values_on_edge(t);
                        return bc.g(x,y) * phi[i];
                    };
                    r[edge[i]] += edge_quadrature(edge_quad_rule,coords,g_times_phi_i);
                }
                else continue;
            }
        }        
        return r;
    }

} // namespace fem