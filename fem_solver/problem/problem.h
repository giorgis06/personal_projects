#pragma once

#include "boundary_conditions.h"
#include "materials/materials.h"
#include "mesh/mesh.h"

namespace fem {

struct PoissonProblem {
  Mesh mesh;
  Materials materials;                     // element tag -> a (epsilon tensor)
  std::function<double(double, double)> f; // charge density over space
  BoundaryConditions bcs;                  // edge tag -> {type,g,kappa}
};

} // namespace fem