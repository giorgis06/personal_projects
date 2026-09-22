#include "mesh.h"   // brings vector, array, map, string, utility
#include "helpers.h"
#include "gmsh.h"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <unordered_map>

namespace fs = std::filesystem;

namespace fem {

using std::vector,std::array,std::map,std::string,std::pair;

// Absolute floor on |signed area|: anything smaller is a collapsed
// triangle, not a small one. Real elements are many orders above this.
const double TOLERANCE_ABSOLUTE_TRIG_AREA = 1e-14;

const array<string,2> ACCEPTED_FILE_TYPES = {".msh",".geo"};
const map<int,int> GMSH_CODE_TO_NODE_COUNT = {{9,6},{8,3},{15, 1}, {1, 2}, {2, 3}};
const map<int,string> GMSH_CODE_TO_ELEMENT_NAME = {{15, "point"}, {1, "line"}, {2, "triangle"}, {8, "line (P2)"}, {9, "triangle (P2)"}};

// Failures validate() can report. Index into VALIDATION_ERRORS with these,
// and append the offending index/count to the message before throwing.
enum class MeshFault {
    EMPTY_MESH, INDEX_OUT_OF_RANGE, REPEATED_NODE, NON_FINITE_COORD,
    TAG_LENGTH_MISMATCH, DEGENERATE_ELEMENT, EDGE_OVERSHARED,
    UNTAGGED_BOUNDARY_EDGE, ORPHAN_NODE, DISCONNECTED_MESH, COUNT
};

const array<string,static_cast<size_t>(MeshFault::COUNT)> VALIDATION_ERRORS = {
    "mesh is empty: needs at least one node and one element",
    "node index out of range in element",
    "element refers to the same node twice: element",
    "coordinate is not finite at node",
    "tag vector length does not match the array it annotates: ",
    "element has (near) zero area: element",
    "edge is shared by more than two elements: edge",
    "boundary edge carries no physical tag: edge",
    "node belongs to no element (empty row in K): node",
    "connectivity check failed "
};

inline string fault_message(MeshFault fault, const string& detail = ""){
    return VALIDATION_ERRORS[static_cast<size_t>(fault)] + detail;
}

MeshData parse_msh(const fs::path& path_to_msh){

    // Create MeshData object through gmsh parser, that will be validated before being turned into Mesh object

    if(!fs::exists(path_to_msh)) throw std::runtime_error("Specified mesh path does not exist: " + path_to_msh.string());
    if(std::find(ACCEPTED_FILE_TYPES.begin(),ACCEPTED_FILE_TYPES.end(),path_to_msh.extension()) == ACCEPTED_FILE_TYPES.end()){
        throw std::runtime_error("Specified file type is not accepted. Accepted file types are: .msh, .geo");
    }
    vector<array<double,2>> node_positions;
    vector<array<int,3>> element_nodes;
    vector<int> element_tags;
    vector<array<int,2>> edge_nodes;
    vector<int> edge_tags;
    vector<int> point_nodes;
    vector<int> point_tags;
    map<string,int> tag_names;

    gmsh::initialize();
    gmsh::option::setNumber("General.Terminal", 1); // Write to stdout
    gmsh::open(path_to_msh);
    if(path_to_msh.extension() != ".msh") gmsh::model::mesh::generate(2);
    
    // 1. NODES

    vector<size_t> node_tags; // The way gmsh stores them - random numbers, need map to my own ids
    vector<double> coords,unused; // Flat vectors that contain the node info needed
    std::unordered_map<size_t,int> tag_to_index;

    gmsh::model::mesh::getNodes(node_tags, coords, unused, -1, -1, false, false); // API does the parsing

    node_positions.resize(node_tags.size()); 
    for(size_t i = 0; i < node_positions.size(); ++i){
        node_positions[i] = {coords[3*i],coords[3*i+1]};
        tag_to_index[node_tags[i]] = i;
    }

    // 2. PHYSICAL GROUPS
    gmsh::vectorpair groups;
    gmsh::model::getPhysicalGroups(groups);
    
    // Iterate over physical groups, like ("glass",tag={10})

    for(auto [dim,phys_tag] : groups){ 
        string name;
        gmsh::model::getPhysicalName(dim,phys_tag,name);
        tag_names[name] = phys_tag;

        vector<int> entities;
        gmsh::model::getEntitiesForPhysicalGroup(dim,phys_tag,entities);

        // Iterate over entities inside one physical groups: 
        // Collections of different elements (eg a patch of triangles, with a contour)

        for(int entity : entities){
            vector<int> types;
            vector<vector<size_t>> elem_tags,elem_nodes;
            gmsh::model::mesh::getElements(types,elem_tags,elem_nodes,dim,entity);

            // getElements returns one block per element type found on this entity:
            //   types[k]      gmsh type code of block k (15 point, 1 line, 2 triangle)
            //   elem_tags[k]  gmsh ids of the elements in block k (only used for the count)
            //   elem_nodes[k] their node tags, flat: element j owns
            //                 elem_nodes[k][n*j] .. elem_nodes[k][n*j + n-1], n = nodes per element
            // We keep only the connectivity (node tags -> our indices) and phys_tag.

            for(size_t k = 0; k < types.size(); ++k){
                string name = GMSH_CODE_TO_ELEMENT_NAME.at(types[k]);
                size_t node_count = static_cast<size_t>(GMSH_CODE_TO_NODE_COUNT.at(types[k]));

                if(name == "triangle"){
                    for(size_t j = 0; j < elem_tags[k].size(); ++j){
                        array<int,3> nodes = {0,0,0};
                        for(size_t l = 0; l < node_count; ++l){
                            nodes[l] = tag_to_index.at(elem_nodes[k][node_count*j+l]);
                        }
                        element_nodes.push_back(nodes);
                        element_tags.push_back(phys_tag);
                    }
                }
                else if(name == "line"){
                    for(size_t j = 0; j < elem_tags[k].size(); ++j){
                        array<int,2> nodes = {0,0};
                        for(size_t l = 0; l < node_count; ++l){
                            nodes[l] = tag_to_index.at(elem_nodes[k][node_count*j+l]);
                        }
                        edge_nodes.push_back(nodes);
                        edge_tags.push_back(phys_tag);
                    }
                }
                else if(name == "point"){
                    for(size_t j = 0; j < elem_tags[k].size(); ++j){
                        point_nodes.push_back(tag_to_index.at(elem_nodes[k][j]));
                        point_tags.push_back(phys_tag);
                    }
                }
                else{
                    throw std::runtime_error("Unsupported element: " + name + " (gmsh code " + std::to_string(types[k]) + ")");
                }
            }
        }
    }

    gmsh::finalize();

    return MeshData(std::move(node_positions),
                    std::move(element_nodes),
                    std::move(element_tags),
                    std::move(edge_nodes),
                    std::move(edge_tags),
                    std::move(point_nodes),
                    std::move(point_tags),
                    std::move(tag_names));
}

void validate(MeshData& mesh_data){
    // Validate eligibility of mesh data,
    // Reorder node ids to match ccw convention
    // Return true if:
    // -> Data was valid
    // -> Optional checks regarding chunkiness succeeded
    // -> And more...?

    // Throw an exception instead of returning true / false? 

    // CHECK EMPTY

    if(mesh_data.Element_Nodes.empty() || mesh_data.Node_Positions.empty()) throw(std::runtime_error(fault_message(MeshFault::EMPTY_MESH)));
    
    // CHECK BOUNDED AND NO REPEATS
    // Every stored index addresses a NODE, so the bound is the node count.

    const int node_count = static_cast<int>(mesh_data.Node_Positions.size());

    for(size_t e = 0; e < mesh_data.Element_Nodes.size(); ++e){
        const auto& tri = mesh_data.Element_Nodes[e];

        // A repeated index means two vertices coincide: zero area, no inverse.
        if(tri[0] == tri[1] || tri[1] == tri[2] || tri[0] == tri[2]){
            throw std::runtime_error(fault_message(MeshFault::REPEATED_NODE, " " + std::to_string(e)));
        }

        for(int id : tri){
            if(id < 0 || id >= node_count){
                throw std::runtime_error(fault_message(MeshFault::INDEX_OUT_OF_RANGE, " " + std::to_string(e) + ": node " + std::to_string(id)));
            }
        }
        
    }

    for(size_t i = 0; i < mesh_data.Edge_Nodes.size(); ++i){
        if(mesh_data.Edge_Nodes[i][0] == mesh_data.Edge_Nodes[i][1]){
            throw std::runtime_error(fault_message(MeshFault::REPEATED_NODE, " (edge) " + std::to_string(i)));
        }
        for(int id : mesh_data.Edge_Nodes[i]){
            if(id < 0 || id >= node_count){
                throw std::runtime_error(fault_message(MeshFault::INDEX_OUT_OF_RANGE, " (edge) " + std::to_string(i) + ": node " + std::to_string(id)));
            }
        }
    }

    for(size_t i = 0; i < mesh_data.Point_Nodes.size(); ++i){
        const int id = mesh_data.Point_Nodes[i];
        if(id < 0 || id >= node_count){
            throw std::runtime_error(fault_message(MeshFault::INDEX_OUT_OF_RANGE, " (point) " + std::to_string(i) + ": node " + std::to_string(id)));
        }
    }

    // CHECK FINITE COORDINATES

    for(size_t i = 0; i < mesh_data.Node_Positions.size(); ++i){
        if(!(std::isfinite(mesh_data.Node_Positions[i][0]) && std::isfinite(mesh_data.Node_Positions[i][1]))){
            throw std::runtime_error(fault_message(MeshFault::NON_FINITE_COORD, " " + std::to_string(i)));
        }
    }

    // CHECK TAG LENGTHS

    // Empty means "untagged, one region"; otherwise one tag per entry.

    if(!mesh_data.Element_Tags.empty() && mesh_data.Element_Tags.size() != mesh_data.Element_Nodes.size()){
        throw std::runtime_error(fault_message(MeshFault::TAG_LENGTH_MISMATCH,
            "Element_Tags " + std::to_string(mesh_data.Element_Tags.size())
            + " vs Element_Nodes " + std::to_string(mesh_data.Element_Nodes.size())));
    }

    if(!mesh_data.Edge_Tags.empty() && mesh_data.Edge_Tags.size() != mesh_data.Edge_Nodes.size()){
        throw std::runtime_error(fault_message(MeshFault::TAG_LENGTH_MISMATCH,
            "Edge_Tags " + std::to_string(mesh_data.Edge_Tags.size())
            + " vs Edge_Nodes " + std::to_string(mesh_data.Edge_Nodes.size())));
    }

    if(!mesh_data.Point_Tags.empty() && mesh_data.Point_Tags.size() != mesh_data.Point_Nodes.size()){
        throw std::runtime_error(fault_message(MeshFault::TAG_LENGTH_MISMATCH,
            "Point_Tags " + std::to_string(mesh_data.Point_Tags.size())
            + " vs Point_Nodes " + std::to_string(mesh_data.Point_Nodes.size())));
    }

    // CHECK |TRIG_AREA| ABOVE TOLERANCE

    for(size_t e = 0; e < mesh_data.Element_Nodes.size(); ++e){
        auto& element = mesh_data.Element_Nodes[e];
        const double area = trig_area(mesh_data.Node_Positions[element[0]],
                                      mesh_data.Node_Positions[element[1]],
                                      mesh_data.Node_Positions[element[2]]);
        if(std::abs(area) < TOLERANCE_ABSOLUTE_TRIG_AREA){
            throw std::runtime_error(fault_message(MeshFault::DEGENERATE_ELEMENT,
                " " + std::to_string(e) + ", area " + std::to_string(area)));
        }

        // ENFORCE CCW WINDING: swapping two indices flips the sign.
        if(area < 0) std::swap(element[0],element[2]);
    }

    // CHECK EDGES ARE CORRECTLY SHARED

    // One pass over the triangles instead of a scan per edge: key every edge by
    // its two node indices, smaller first, so the two owners of an interior edge
    // produce the same key. count == 2 interior, == 1 boundary, > 2 broken mesh.

    map<pair<int,int>,int> edge_owners;

    for(const auto& element : mesh_data.Element_Nodes){
        for(int v = 0; v < 3; ++v){
            int a = element[v], b = element[(v+1)%3];
            if(a > b) std::swap(a,b);
            ++edge_owners[{a,b}];
        }
    }

    // The edges the parser tagged, keyed the same way. Interior edges may be
    // tagged too (a material interface), so this is only used one way round:
    // every geometric boundary edge must appear here.

    map<pair<int,int>,int> tagged_edges;
    for(size_t i = 0; i < mesh_data.Edge_Nodes.size(); ++i){
        int a = mesh_data.Edge_Nodes[i][0], b = mesh_data.Edge_Nodes[i][1];
        if(a > b) std::swap(a,b);
        tagged_edges[{a,b}] = static_cast<int>(i);
    }

    for(const auto& [edge, owners] : edge_owners){
        const string where = " (" + std::to_string(edge.first) + "," + std::to_string(edge.second) + ")";

        if(owners > 2){
            throw std::runtime_error(fault_message(MeshFault::EDGE_OVERSHARED,
                where + ": " + std::to_string(owners) + " elements"));
        }
        if(owners == 1 && tagged_edges.find(edge) == tagged_edges.end()){
            throw std::runtime_error(fault_message(MeshFault::UNTAGGED_BOUNDARY_EDGE, where));
        }
    }

    // CHECK ORPHAN NODES

    // Valence = how many triangles touch a node. Zero means an empty row in K,
    // i.e. a singular matrix. Counts triangles only. 
    // A node held by a boundary edge but by no triangle is the bug being caught.

    vector<int> node_frequency(mesh_data.Node_Positions.size(), 0);

    for(const auto& element : mesh_data.Element_Nodes){
        for(int id : element) ++node_frequency[id];
    }

    for(size_t i = 0; i < node_frequency.size(); ++i){
        if(node_frequency[i] == 0){
            throw std::runtime_error(fault_message(MeshFault::ORPHAN_NODE,
                " " + std::to_string(i)));
        }
    }

    // CHECK PLANAR GRAPH CONNECTIVITY
    // See helpers.h for details on the implementation:
    // Traverse the dual graph of the mesh, ie nodes = triangles, 
    // Edges between triangles = edges
    // If BFS visits all, connected.

    if(!is_connected(dual_adjacency(mesh_data.Element_Nodes))){
        throw std::runtime_error(fault_message(MeshFault::DISCONNECTED_MESH));
    }

    // IMPLY NUMBER OF HOLES
    // V - E + F_triangles = 1 - Holes, since F = F_triangles + 1 (outer face) + Holes.
    // Derived from the mesh, so it cannot contradict Euler: it is a number to
    // eyeball against the geometry, not a pass/fail test.
    // V = mesh_data.Node_Positions.size()
    // E = edge_owners.size()
    // F_triangles = mesh_data.Element_Nodes.size()

    const long long V = static_cast<long long>(mesh_data.Node_Positions.size());
    const long long E = static_cast<long long>(edge_owners.size());
    const long long F = static_cast<long long>(mesh_data.Element_Nodes.size());

    std::cout << "Implied holes from mesh: " << (1 - V + E - F) << "\n";
    
}

Mesh load_mesh(/*path/to/.msh*/){
    //MeshData mesh = parse_msh(/*path/to/.msh*/);
}

}   // namespace fem
