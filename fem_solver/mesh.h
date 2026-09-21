// TODO(elsewhere)
//  [ ] load_msh(path) -> Mesh          (parsing only, no interpretation)
//  [ ] make_unit_square(nx,ny) -> Mesh (Phase 1, same type)
//  [ ] validate(mesh, quality) -> report (Euler, area sum, edge census,
//                                         range check, degenerate elements)
//  [ ] BoundaryConditions: tag -> (type, value) -- separate from Mesh
//  [ ] Materials: tag -> (eps, mu, sigma) -- separate from Mesh
//  [ ] DOF layer: do NOT assume numDofs()==numNodes() anywhere in assembly

#pragma once

#include <vector>
#include <array>
#include <cstddef>
#include <map>
#include <string>
#include <utility>
#include <exception>

const std::array<double,2> DOUBLE_ZERO_2D{0.0, 0.0};
const std::array<int,3> INT_ZERO_3D{0,0,0};

class Mesh{
    // The object that stores the positions of Nodes and Node IDs of
    // the vertices of each element/triangle.
    //
    // INVARIANTS (enforced by validate(), assumed by everything downstream):
    //   - every index in NID_Elements is in [0, numNodes())
    //   - no degenerate (zero-area) elements
    //   - all coordinates finite
    //   - Element_Tags / Edge_Tags are empty, or the same length as the
    //     array they annotate (NID_Elements / Boundary_Edges)
    //   - winding: every element is counter-clockwise, i.e. its signed area
    //     0.5*((x1-x0)*(y2-y0) - (x2-x0)*(y1-y0)) is > 0. Enforced by
    //     validate() swapping two indices where it is negative. Costs no
    //     storage -- it only constrains the ORDER of the three ints.
    //     Consumers may therefore use det J directly, not |det J|.

    private:
        std::vector<std::array<double,2>> Positions_Nodes;
        std::vector<std::array<int,3>> NID_Elements;

        // Per-element region id ($PhysicalSurface). Parallel to NID_Elements.
        // Materials (eps, mu, sigma) map tag -> values and live OUTSIDE Mesh,
        // same as BoundaryConditions. Empty when the mesh has one region.
        std::vector<int> Element_Tags;

        // Boundary topology. Boundary_Edges and Edge_Tags are parallel:
        // Edge_Tags[i] is the gmsh physical group id of Boundary_Edges[i].
        // Which tag means Dirichlet vs Neumann is NOT stored here -- that is
        // problem data and lives in a separate BoundaryConditions struct.
        std::vector<std::array<int,2>> Boundary_Edges;
        std::vector<int> Edge_Tags;
        std::map<std::string,int> Tag_Names;   // "wall" -> 3
    public:
        // NOTE: member init order must match declaration order above.
        Mesh(int node_number,int element_number):
        Positions_Nodes(node_number, DOUBLE_ZERO_2D),
        NID_Elements(element_number, INT_ZERO_3D)
        {}

        // Parser ctor: build the vectors locally, then move them in. A Mesh
        // built this way is never half-filled.
        Mesh(std::vector<std::array<double,2>> positions,
             std::vector<std::array<int,3>> elements,
             std::vector<int> element_tags = {},
             std::vector<std::array<int,2>> boundary_edges = {},
             std::vector<int> edge_tags = {},
             std::map<std::string,int> tag_names = {}):
        Positions_Nodes(std::move(positions)),
        NID_Elements(std::move(elements)),
        Element_Tags(std::move(element_tags)),
        Boundary_Edges(std::move(boundary_edges)),
        Edge_Tags(std::move(edge_tags)),
        Tag_Names(std::move(tag_names))
        {}

        // Read-only views. Assembly takes `const Mesh&` and goes through these.
        const std::vector<std::array<double,2>>& nodePositions() const { return Positions_Nodes; }
        const std::vector<std::array<int,3>>& elementNodeIDs() const { return NID_Elements; }
        std::size_t numNodes() const { return Positions_Nodes.size(); }
        std::size_t numElements() const { return NID_Elements.size(); }

        const std::vector<int>& elementTags() const { return Element_Tags; }
        const std::vector<std::array<int,2>>& boundaryEdges() const { return Boundary_Edges; }
        const std::vector<int>& edgeTags() const { return Edge_Tags; }
        const std::map<std::string,int>& tagNames() const { return Tag_Names; }
        std::size_t numBoundaryEdges() const { return Boundary_Edges.size(); }
};

struct MeshData{
    // Raw data produced by the parser, to be validated

    std::vector<std::array<double,2>> Positions_Nodes;
    std::vector<std::array<int,3>> NID_Elements;
    std::vector<int> Element_Tags;
    std::vector<std::array<int,2>> Boundary_Edges;
    std::vector<int> Edge_Tags;
    std::map<std::string,int> Tag_Names;

};

MeshData parse_msh(/*path/to/.msh*/){}

bool validate(MeshData& mesh_data){
    // Validate eligibility of mesh data,
    // Reorder node ids to match ccw convention
    // Return true if:
    // -> Data was valid
    // -> Optional checks regarding chunkiness succeeded
    // -> And more...?

    // Throw an exception instead of returning true / false? 
}

Mesh load_mesh(/*path/to/.msh*/){
    MeshData mesh = parse_msh(/*path/to/.msh*/);
    try{
        validate(mesh);
        // copy mesh into the constructor of Mesh
        // use std::move for efficiency ?
    }
    catch(e){
        printf(/*nice try*/);
    };
    
}