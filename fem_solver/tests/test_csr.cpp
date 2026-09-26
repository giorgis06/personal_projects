#include "doctest.h"
#include "linalg/csr.h"

using namespace fem;

//     [ 4  0  1 ]
// A = [ 0  3  0 ]
//     [ 1  0  5 ]

TEST_CASE("to_csr: shuffled triplets with a split duplicate"){
    // (0,0) arrives as 3 + 1, the way two triangles sharing a node contribute
    CSR K = to_csr({{2,2,5},{0,2,1},{1,1,3},{0,0,3},{2,0,1},{0,0,1}}, 3);

    CHECK(K.n == 3);
    CHECK(K.values  == vector<double>{4, 1, 3, 1, 5});
    CHECK(K.col_idx == vector<int>{0, 2, 1, 0, 2});
    CHECK(K.row_ptr == vector<int>{0, 2, 3, 5});
}

TEST_CASE("to_csr: empty rows"){
    // Only rows 0 and 2 have entries in a 4x4
    CSR K = to_csr({{2,2,5},{0,0,1}}, 4);

    CHECK(K.values  == vector<double>{1, 5});
    CHECK(K.col_idx == vector<int>{0, 2});
    CHECK(K.row_ptr == vector<int>{0, 1, 1, 2, 2});
}

TEST_CASE("to_csr: empty input gives a valid all-zero matrix"){
    CSR K = to_csr({}, 3);

    CHECK(K.n == 3);
    CHECK(K.values.empty());
    CHECK(K.col_idx.empty());
    CHECK(K.row_ptr == vector<int>{0, 0, 0, 0});
}
