#pragma once

#include <functional>
#include <map>

namespace fem{

enum class BCType {Dirichlet, // u = g_D 
                   Neumann,   // n_hat * [a * grad(u)] = g_N , where a is a tensor 
                   Robin      // -n_hat * [a * grad(u)] = kappa * u - [kappa * g_D + g_N] , where kappa > 0 and a a tensor
                   };

struct BoundaryCondition{
    BCType type;
    std::function<double(double,double)> g; // g_D for Dirichlet, g_N for Neumann, kappa*g_D + g_N for Robin
    double kappa = 0.0; // For Robin BCs 
};

using BoundaryConditions = std::map<int,BoundaryCondition>;

} //namespace fem