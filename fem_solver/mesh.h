#pragma once

#include <vector>
#include <array>
#include <cstddef>
#include <map>
#include <string>
#include <filesystem>
#include <utility>

namespace fem {

// Inside the namespace, so these short names stay in fem and never reach the
// global scope of whoever includes this header.
using std::vector,std::array,std::map,std::string,std::size_t,std::move;

const array<double,2> DOUBLE_ZERO_2D{0.0, 0.0};
const array<int,3> INT_ZERO_3D{0,0,0};

class Mesh{
    // The object that stores the positions of Nodes and Node IDs of
    // the vertices of each element/triangle.
    //
    // INVARIANTS (enforced by validate(), assumed by everything downstream):
    //   - every index in Element_Nodes is in [0, numNodes())
    //   - no degenerate (zero-area) elements
    //   - all coordinates finite
    //   - Element_Tags / Edge_Tags / Point_Tags are empty, or the same length
    //     as the array they annotate (Element_Nodes / Edge_Nodes /
    //     Point_Nodes)
    //   - winding: every element is counter-clockwise, i.e. its signed area
    //     0.5*((x1-x0)*(y2-y0) - (x2-x0)*(y1-y0)) is > 0. Enforced by
    //     validate() swapping two indices where it is negative. Costs no
    //     storage -- it only constrains the ORDER of the three ints.
    //     Consumers may therefore use det J directly, not |det J|.

    private:
        vector<array<double,2>> Node_Positions;
        vector<array<int,3>> Element_Nodes;

        // Per-element region id ($PhysicalSurface). Parallel to Element_Nodes.
        // Materials (eps, mu, sigma) map tag -> values and live OUTSIDE Mesh,
        // same as BoundaryConditions. Empty when the mesh has one region.
        vector<int> Element_Tags;

        // Boundary topology. Edge_Nodes and Edge_Tags are parallel:
        // Edge_Tags[i] is the gmsh physical group id of Edge_Nodes[i].
        // Which tag means Dirichlet vs Neumann is NOT stored here -- that is
        // problem data and lives in a separate BoundaryConditions struct.
        vector<array<int,2>> Edge_Nodes;
        vector<int> Edge_Tags;

        // Tagged single nodes ($PhysicalPoint), e.g. a point charge location.
        // Point_Tags is parallel to Point_Nodes; the value carried by the tag
        // (charge, pinned potential) lives OUTSIDE Mesh, like Materials.
        vector<int> Point_Nodes;
        vector<int> Point_Tags;
        map<string,int> Tag_Names;   // "wall" -> 3
    public:
        // NOTE: member init order must match declaration order above.
        Mesh(int node_number,int element_number):
        Node_Positions(node_number, DOUBLE_ZERO_2D),
        Element_Nodes(element_number, INT_ZERO_3D)
        {}

        // Parser ctor: build the vectors locally, then move them in. A Mesh
        // built this way is never half-filled.
        Mesh(vector<array<double,2>> positions,
             vector<array<int,3>> elements,
             vector<int> element_tags = {},
             vector<array<int,2>> edge_nodes = {},
             vector<int> edge_tags = {},
             vector<int> point_nodes = {},
             vector<int> point_tags = {},
             map<string,int> tag_names = {}):
        Node_Positions(move(positions)),
        Element_Nodes(move(elements)),
        Element_Tags(move(element_tags)),
        Edge_Nodes(move(edge_nodes)),
        Edge_Tags(move(edge_tags)),
        Point_Nodes(move(point_nodes)),
        Point_Tags(move(point_tags)),
        Tag_Names(move(tag_names))
        {}

        // Read-only views. Assembly takes `const Mesh&` and goes through these.
        const vector<array<double,2>>& nodePositions() const { return Node_Positions; }
        const vector<array<int,3>>& elementNodes() const { return Element_Nodes; }
        size_t numNodes() const { return Node_Positions.size(); }
        size_t numElements() const { return Element_Nodes.size(); }

        const vector<int>& elementTags() const { return Element_Tags; }
        const vector<array<int,2>>& edgeNodes() const { return Edge_Nodes; }
        const vector<int>& edgeTags() const { return Edge_Tags; }
        const vector<int>& pointNodes() const { return Point_Nodes; }
        const vector<int>& pointTags() const { return Point_Tags; }
        const map<string,int>& tagNames() const { return Tag_Names; }
        size_t numEdges() const { return Edge_Nodes.size(); }
        size_t numPoints() const { return Point_Nodes.size(); }
};

struct MeshData{
    // Raw data produced by the parser, to be validated

    vector<array<double,2>> Node_Positions;
    vector<array<int,3>> Element_Nodes;
    vector<int> Element_Tags;
    vector<array<int,2>> Edge_Nodes;
    vector<int> Edge_Tags;
    vector<int> Point_Nodes;
    vector<int> Point_Tags;
    map<string,int> Tag_Names;

    MeshData() = default;

    // Same shape as Mesh's parser ctor: pass locals with move.
    MeshData(vector<array<double,2>> positions,
             vector<array<int,3>> elements,
             vector<int> element_tags = {},
             vector<array<int,2>> edge_nodes = {},
             vector<int> edge_tags = {},
             vector<int> point_nodes = {},
             vector<int> point_tags = {},
             map<string,int> tag_names = {}):
    Node_Positions(move(positions)),
    Element_Nodes(move(elements)),
    Element_Tags(move(element_tags)),
    Edge_Nodes(move(edge_nodes)),
    Edge_Tags(move(edge_tags)),
    Point_Nodes(move(point_nodes)),
    Point_Tags(move(point_tags)),
    Tag_Names(move(tag_names))
    {}
};

MeshData parse_msh(const std::filesystem::path& path_to_msh);
void validate(MeshData& mesh_data);
Mesh load_mesh(const std::filesystem::path& path_to_msh);


}   // namespace fem
