#include "mesh.h"   // brings vector, array, map, string, utility

#include "gmsh.h"

#include <algorithm>
#include <filesystem>
#include <stdexcept>
#include <unordered_map>

using std::vector,std::array,std::map,std::string;
namespace fs = std::filesystem;

const array<string,2> ACCEPTED_FILE_TYPES = {".msh",".geo"};
const map<int,int> GMSH_CODE_TO_NODE_COUNT = {{9,6},{8,3},{15, 1}, {1, 2}, {2, 3}};
const map<int,string> GMSH_CODE_TO_ELEMENT_NAME = {{15, "point"}, {1, "line"}, {2, "triangle"}, {8, "line (P2)"}, {9, "triangle (P2)"}};

// Failures validate() can report. Index into VALIDATION_ERRORS with these,
// and append the offending index/count to the message before throwing.
enum class MeshFault {
    EMPTY_MESH, INDEX_OUT_OF_RANGE, REPEATED_NODE, NON_FINITE_COORD,
    TAG_LENGTH_MISMATCH, DEGENERATE_ELEMENT, EDGE_OVERSHARED,
    UNTAGGED_BOUNDARY_EDGE, ORPHAN_NODE, EULER_MISMATCH, COUNT
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
    "Euler check V-E+F failed, expected 1-holes, got "
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
    vector<array<double,2>> positions_nodes;
    vector<array<int,3>> node_id_per_element;
    vector<int> element_tags;
    vector<array<int,2>> boundary_edges;
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

    positions_nodes.resize(node_tags.size()); 
    for(size_t i = 0; i < positions_nodes.size(); ++i){
        positions_nodes[i] = {coords[3*i],coords[3*i+1]};
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
                        node_id_per_element.push_back(nodes);
                        element_tags.push_back(phys_tag);
                    }
                }
                else if(name == "line"){
                    for(size_t j = 0; j < elem_tags[k].size(); ++j){
                        array<int,2> nodes = {0,0};
                        for(size_t l = 0; l < node_count; ++l){
                            nodes[l] = tag_to_index.at(elem_nodes[k][node_count*j+l]);
                        }
                        boundary_edges.push_back(nodes);
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

    return MeshData(std::move(positions_nodes),
                    std::move(node_id_per_element),
                    std::move(element_tags),
                    std::move(boundary_edges),
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


}

Mesh load_mesh(/*path/to/.msh*/){
    //MeshData mesh = parse_msh(/*path/to/.msh*/);
}