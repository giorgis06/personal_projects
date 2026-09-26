#include "doctest.h"
#include "mesh/mesh.h"
#include "helpers.h"

#include <cmath>
#include <limits>
#include <stdexcept>

using namespace fem;
using doctest::Contains;

// Unit square as two CCW triangles, every boundary edge tagged:
//
//   3 --- 2
//   |   / |
//   | /   |
//   0 --- 1
static MeshData valid_square(){
    return MeshData({{0,0},{1,0},{1,1},{0,1}},
                    {{0,1,2},{0,2,3}},
                    {10,10},
                    {{0,1},{1,2},{2,3},{3,0}},
                    {1,1,1,1});
}

TEST_CASE("validate: a valid mesh passes"){
    MeshData m = valid_square();
    CHECK_NOTHROW(validate(m));
}

TEST_CASE("validate: a tagged interior edge (material interface) is allowed"){
    MeshData m = valid_square();
    m.Edge_Nodes.push_back({0,2});   // the diagonal, shared by both triangles
    m.Edge_Tags.push_back(2);
    CHECK_NOTHROW(validate(m));
}

TEST_CASE("validate: clockwise elements are flipped to counter-clockwise"){
    MeshData m = valid_square();
    m.Element_Nodes[0] = {0,2,1};    // clockwise
    validate(m);
    for(const auto& e : m.Element_Nodes){
        CHECK(trig_area({m.Node_Positions[e[0]], m.Node_Positions[e[1]], m.Node_Positions[e[2]]}) > 0);
    }
}

TEST_CASE("validate: each fault is reported"){
    SUBCASE("empty mesh"){
        MeshData m;
        CHECK_THROWS_WITH_AS(validate(m), Contains("mesh is empty"), std::runtime_error);
    }
    SUBCASE("repeated node in an element"){
        MeshData m = valid_square();
        m.Element_Nodes[0] = {0,0,2};
        CHECK_THROWS_WITH_AS(validate(m), Contains("same node twice"), std::runtime_error);
    }
    SUBCASE("node index out of range"){
        MeshData m = valid_square();
        m.Element_Nodes[0] = {0,1,7};
        CHECK_THROWS_WITH_AS(validate(m), Contains("out of range"), std::runtime_error);
    }
    SUBCASE("non-finite coordinate"){
        MeshData m = valid_square();
        m.Node_Positions[2][0] = std::numeric_limits<double>::quiet_NaN();
        CHECK_THROWS_WITH_AS(validate(m), Contains("not finite"), std::runtime_error);
    }
    SUBCASE("tag vector length mismatch"){
        MeshData m = valid_square();
        m.Element_Tags = {10};
        CHECK_THROWS_WITH_AS(validate(m), Contains("tag vector length"), std::runtime_error);
    }
    SUBCASE("degenerate element"){
        MeshData m = valid_square();
        m.Node_Positions[2] = {2,0};  // triangle {0,1,2} becomes collinear
        CHECK_THROWS_WITH_AS(validate(m), Contains("zero area"), std::runtime_error);
    }
    SUBCASE("edge shared by more than two elements"){
        MeshData m = valid_square();
        m.Node_Positions.push_back({0.5,-1});
        m.Element_Nodes.push_back({0,4,2});   // a third triangle on the diagonal (0,2)
        m.Element_Tags.push_back(10);
        CHECK_THROWS_WITH_AS(validate(m), Contains("more than two elements"), std::runtime_error);
    }
    SUBCASE("untagged boundary edge"){
        MeshData m = valid_square();
        m.Edge_Nodes.pop_back();
        m.Edge_Tags.pop_back();
        CHECK_THROWS_WITH_AS(validate(m), Contains("no physical tag"), std::runtime_error);
    }
    SUBCASE("orphan node"){
        MeshData m = valid_square();
        m.Node_Positions.push_back({5,5});
        CHECK_THROWS_WITH_AS(validate(m), Contains("belongs to no element"), std::runtime_error);
    }
    SUBCASE("disconnected mesh"){
        // Two triangles touching only at node 2: no shared edge
        MeshData m({{0,0},{1,0},{1,1},{2,1},{2,2}},
                   {{0,1,2},{2,3,4}},
                   {10,10},
                   {{0,1},{1,2},{2,0},{2,3},{3,4},{4,2}},
                   {1,1,1,1,1,1});
        CHECK_THROWS_WITH_AS(validate(m), Contains("connectivity"), std::runtime_error);
    }
}

// Loading runs gmsh, so each fixture is meshed once and shared between cases.
static const Mesh& square_mesh(){
    static const Mesh mesh = load_mesh("tests/data/square.geo");
    return mesh;
}

TEST_CASE("load_mesh: unit square fixture"){
    const Mesh& mesh = square_mesh();

    REQUIRE(mesh.numNodes() > 0);
    REQUIRE(mesh.numElements() > 0);
    CHECK(mesh.elementTags().size() == mesh.numElements());
    CHECK(mesh.edgeTags().size() == mesh.numEdges());

    // Every element CCW, total area 1
    double total = 0.0;
    for(const auto& e : mesh.elementNodes()){
        const auto& p = mesh.nodePositions();
        double a = trig_area({p[e[0]], p[e[1]], p[e[2]]});
        CHECK(a > 0);
        total += a;
    }
    CHECK(total == doctest::Approx(1.0));

    // Named physical groups come through
    for(const char* name : {"bottom", "right", "top", "left", "air"}){
        CHECK(mesh.tagNames().count(name) == 1);
    }
}

TEST_CASE("load_mesh: missing file and wrong extension throw"){
    CHECK_THROWS_WITH_AS(load_mesh("tests/data/does_not_exist.geo"), Contains("does not exist"), std::runtime_error);
    CHECK_THROWS_WITH_AS(load_mesh("Makefile"), Contains("not accepted"), std::runtime_error);
}
