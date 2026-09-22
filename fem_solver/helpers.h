#pragma once

#include <algorithm>
#include <array>
#include <cstddef>
#include <map>
#include <queue>
#include <utility>
#include <vector>

using std::pair,std::map,std::array,std::queue,std::vector;

inline double trig_area(const array<double,2>& n1, const array<double,2>& n2, const array<double,2>& n3){
    return 0.5*((n2[0]-n1[0])*(n3[1]-n1[1]) - (n3[0]-n1[0])*(n2[1]-n1[1]));
}

// Dual graph of a simplex (triangle, tetrahedron) mesh: one vertex per element, one edge per facet
// shared by two elements. N is the vertices per element, so a facet has N-1
// of them: N=3 triangles sharing edges, N=4 tets sharing faces.
// The facet key is sorted, so both owners of a facet produce the same key.

// Returns adjacency[e] = the elements sharing a facet with element e.
//
//   input  {0,1,2}, {1,2,3}      two triangles sharing edge (1,2)
//   output adjacency[0] = {1}
//          adjacency[1] = {0}
template<std::size_t N>
inline vector<vector<int>> dual_adjacency(const vector<array<int,N>>& elements){
    // Pass 1: who owns each facet. An element has N facets, one per vertex
    // left out: drop vertex 0 of {0,1,2} and you get edge (1,2).
    map<array<int,N-1>,vector<int>> facet_owners;

    for(std::size_t e = 0; e < elements.size(); ++e){
        for(std::size_t skip = 0; skip < N; ++skip){
            // Copy the element's vertices except `skip`; w walks the facet.
            array<int,N-1> facet{};
            for(std::size_t v = 0, w = 0; v < N; ++v){
                if(v != skip) facet[w++] = elements[e][v];
            }
            // Sorting makes the key independent of winding, so the two owners
            // of a shared facet (which store it in opposite order) collide.
            std::sort(facet.begin(), facet.end());
            facet_owners[facet].push_back(static_cast<int>(e));
        }
    }

    // Pass 2: a facet with 2 owners is one link in the dual graph. 1 owner is a
    // boundary facet (no neighbour), and >2 means a non-manifold mesh, which
    // validate() rejects before it gets here.
    vector<vector<int>> adjacency(elements.size());
    for(const auto& [facet, owners] : facet_owners){
        if(owners.size() == 2){
            adjacency[owners[0]].push_back(owners[1]);
            adjacency[owners[1]].push_back(owners[0]);
        }
    }
    return adjacency;
}

// BFS over the dual graph: true when every element is reachable from element 0,
// i.e. the mesh is a single piece. Elements touching only at a node are NOT
// connected here, which is the point -- that is a pinched mesh, not one body.
inline bool is_connected(const vector<vector<int>>& adjacency){
    if(adjacency.empty()) return true;

    vector<char> seen(adjacency.size(), 0);
    queue<int> to_visit;

    seen[0] = 1;                 // mark on PUSH, not on pop, or a shared
    to_visit.push(0);            // neighbour gets queued twice
    std::size_t reached = 1;

    while(!to_visit.empty()){
        const int current = to_visit.front();
        to_visit.pop();

        for(int neighbour : adjacency[current]){
            if(!seen[neighbour]){
                seen[neighbour] = 1;
                ++reached;
                to_visit.push(neighbour);
            }
        }
    }
    return reached == adjacency.size();
}
