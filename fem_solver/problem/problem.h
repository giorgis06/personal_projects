#pragma once

#include "mesh/mesh.h"
#include "materials/materials.h"
#include "boundary_conditions.h"

namespace fem{

struct PoissonProblem{
    Mesh mesh;
    Materials materials;                        // element tag -> a (epsilon tensor)
    std::function<double(double,double)> f;     // charge density over space
    BoundaryConditions bcs;                     // edge tag -> {type,g,kappa}
};

} // namespace fem