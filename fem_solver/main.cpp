#include "mesh.h"
#include "csr.h"
#include <iostream>

int main(){
    fem::Mesh mesh = fem::load_mesh("cap.msh");
    std::cout << mesh.numNodes() << " nodes, " << mesh.numElements() << " elements\n" << mesh.numEdges();
}
