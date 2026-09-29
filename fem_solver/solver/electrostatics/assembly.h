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

    inline array<vector<int>,2> general2free_dirichlet(const PoissonProblem& problem){
        const Mesh& m = problem.mesh;
        vector<int> g2f(m.numNodes(),-1);
        vector<int> g2d(m.numNodes(),-1);
        // Parse the nodes. If free, map id to free id
        // If Dirichlet map id to dirichlet id 

        int counter_free = 0,counter_dir = 0;
        for(size_t iEdge = 0; iEdge < m.numEdges(); iEdge++){
            auto it = problem.bcs.find(m.edgeTags()[iEdge]); // tags without a BC (e.g. material interfaces) are skipped
            if(it != problem.bcs.end() && it->second.type == BCType::Dirichlet){
                if(g2d[m.edgeNodes()[iEdge][0]] == -1) g2d[m.edgeNodes()[iEdge][0]] = counter_dir++;
                if(g2d[m.edgeNodes()[iEdge][1]] == -1) g2d[m.edgeNodes()[iEdge][1]] = counter_dir++;
            }
        }
        for(size_t iNode = 0; iNode < m.numNodes(); iNode++){
            if(g2d[iNode] == -1) g2f[iNode] = counter_free++;
        }

        return {std::move(g2f),std::move(g2d)};
    }

    inline int number_of_free_nodes(const vector<int>& g2f){
        int result = 0;
        for(size_t i = 0; i < g2f.size(); ++i) if(g2f[i] != -1) result++;
        return result;
    }

    inline CSR assemble_K_ff(const CSR& K,
                             const vector<int>& g2f,
                             int num_free){
        return extract_principal_submatrix(K,g2f,num_free);
    }

    inline vector<double> assemble_K_fd_times_g(const CSR& K,
                                                const vector<int>& g2f,
                                                const vector<int>& g2d,
                                                const vector<double>& g,
                                                int num_free){
        // K_FD g = (K u_D)_F, where u_D is g on the Dirichlet nodes and 0 on the free ones:
        // the free columns of K multiply zeros, so only the FD block contributes.
        // g is in Dirichlet numbering, g[g2d[node]].
        vector<double> u_D(K.n,0.0);
        for(int i = 0; i < K.n; ++i){
            if(g2d[i] != -1) u_D[i] = g[g2d[i]];
        }
        vector<double> K_u_D(K.n);
        spmv(K,u_D,K_u_D);
        return extract_principal_subvector(K_u_D,g2f,num_free);
    }

    inline vector<double> assemble_b_plus_r_f(const vector<double>& b_plus_r,
                                              const vector<int>& g2f,
                                              int num_free){
        return extract_principal_subvector(b_plus_r,g2f,num_free);
    }

    inline vector<double> assemble_g(const PoissonProblem& problem,
                                     const vector<int>& g2d,
                                     int num_dirichlet){
        // g_D evaluated at every Dirichlet node, in Dirichlet numbering: g[g2d[node]].
        // Corner where two Dirichlet edges with different g_D meet: the last edge wins.
        // Fine if g_D is continuous there, otherwise the problem itself is ill-posed at that point.
        const Mesh& m = problem.mesh;
        vector<double> g(num_dirichlet,0.0);

        for(size_t iEdge = 0; iEdge < m.numEdges(); ++iEdge){
            auto it = problem.bcs.find(m.edgeTags()[iEdge]);
            if(it == problem.bcs.end() || it->second.type != BCType::Dirichlet) continue;

            for(int node : m.edgeNodes()[iEdge]){
                const array<double,2>& p = m.nodePositions()[node];
                g[g2d[node]] = it->second.g(p[0],p[1]);
            }
        }
        return g;
    }

    inline vector<double> assemble_full_solution(const vector<double>& free_solution,
                                                 const vector<double>& dir_solution,
                                                 const vector<int>& g2f,
                                                 const vector<int>& g2d)
    {
        const int n = static_cast<int>(g2f.size());
        if(free_solution.size() + dir_solution.size() != g2f.size()) throw std::runtime_error("In assemble_full_solution: free and Dirichlet parts don't add up to the number of nodes, (dimFree,dimDir,numNodes) = (" + std::to_string(free_solution.size()) + ", " + std::to_string(dir_solution.size()) + ", " + std::to_string(n) + ")");
        vector<double> solution(n,0.0);
        for(int i = 0; i < n; ++i)
            solution[i] = (g2f[i] != -1) ? free_solution[g2f[i]] : dir_solution[g2d[i]];
        return solution;
    }

} // namespace fem