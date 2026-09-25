#pragma once

#include <utility>
#include <vector>
#include <array>
#include <cmath>
#include "helpers.h"


namespace fem{

    using std::pair,std::array,std::vector;
    
    // The idea is for any function f, we have:
    // Integral over triangle = Σ_i (w_i  * f(Σ_j (λ_j*N_j))) * |K|
    // eg for centroid its |K| * f(1/3*(N1+N2+N3))

    struct TriQuadRule{
        vector<array<double,3>> Bary; // (λ0, λ1, λ2) per point
        vector<double> Weights;       // sum to 1, multiply by area
    };

    const TriQuadRule CENTROID = { {{1.0/3, 1.0/3, 1.0/3}}, {1.0} };

    struct EdgeQuadRule {
        std::vector<double> T;        // parameter in [0,1], x = (1-t) p0 + t p1
        std::vector<double> Weights;  // sum to 1, multiply by length
    };

    const EdgeQuadRule MIDPOINT = { {1.0/2},{1.0}};

    template<class F>
    double triangle_quadrature(const TriQuadRule& Q, const array<array<double,2>,3>& T, F&& f){
        
        double result = 0.0;

        // Integral over triangle = Σ_i (w_i  * f(Σ_j (λ_j*N_j))) * |K|

        for(std::size_t i = 0; i < Q.Bary.size(); ++i){
            
            array<double,3> arr = Q.Bary[i];
            array<double,2> point = {0.0,0.0};

            for(std::size_t j = 0; j < arr.size(); ++j){
                point[0] += arr[j]*T[j][0];
                point[1] += arr[j]*T[j][1];
            }

            result += Q.Weights[i]* f(point[0],point[1]);
        }
        return result * trig_area(T);
    }

    template<class F>
    double edge_quadrature(const EdgeQuadRule& Q, const array<array<double,2>,2>& E, F&& f){

        double result = 0.0;

        // Integral over edge = Σ_i (w_i * f((1-t_i)*N_0 + t_i*N_1)) * |E|

        for(std::size_t i = 0; i < Q.T.size(); ++i){

            double t = Q.T[i];
            array<double,2> point = {(1-t)*E[0][0] + t*E[1][0],
                                     (1-t)*E[0][1] + t*E[1][1]};

            result += Q.Weights[i] * f(point[0],point[1]);
        }
        double length = std::hypot(E[1][0]-E[0][0], E[1][1]-E[0][1]);
        return result * length;
    }

} //namespace fem
