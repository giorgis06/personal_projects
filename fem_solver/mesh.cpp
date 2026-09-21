#include "mesh.h"
#include "gmsh.h"

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