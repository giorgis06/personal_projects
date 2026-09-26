#include "solver/electrostatics/assembly.h"
#include <cmath>
#include <iostream>
#include <numeric>

int main(){
    // Cylindrical capacitor: glass (tag 10) around the inner electrode, air (tag 11) outside.
    fem::Materials materials;
    materials[10] = {{4.0, 4.0, 0.0}, {}, {}};   // glass, eps_r = 4
    materials[11] = {{1.0, 1.0, 0.0}, {}, {}};   // air

    // Placeholder charge density: a Gaussian blob in the air region
    auto rho = [](double x, double y){ return std::exp(-((x - 1.0)*(x - 1.0) + y*y) / 0.02); };

    fem::PoissonProblem problem{fem::load_mesh("meshes/cap.msh"), materials, rho, {}};
    std::cout << problem.mesh.numNodes() << " nodes, " << problem.mesh.numElements() << " elements, "
              << problem.mesh.numEdges() << " boundary/interface edges\n";

    fem::CSR K = fem::assemble_stiffness(problem, fem::CENTROID);
    std::cout << "K: " << K.n << " x " << K.n << ", " << K.values.size() << " nonzeros ("
              << static_cast<double>(K.values.size()) / K.n << " per row)\n";

    std::vector<double> b = fem::assemble_load(problem, fem::DEGREE_2);
    std::cout << "b: sum = " << std::accumulate(b.begin(), b.end(), 0.0)
              << " (total charge; the blob integrates to ~" << M_PI * 0.02 << ")\n";

    // Next: boundary terms, Dirichlet elimination, CG solve
}
