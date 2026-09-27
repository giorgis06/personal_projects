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

TEST_CASE("add_csr: overlapping, disjoint and empty rows"){
    //     [ 1  0  2 ]       [ 3  4  0 ]       [ 4  4  2 ]
    // A = [ 0  0  0 ]   B = [ 0  0  0 ]   ->  [ 0  0  0 ]
    //     [ 0  5  0 ]       [ 6  0  7 ]       [ 6  5  7 ]
    // Row 0: overlap at col 0, one entry each only in A / B. Row 1: empty in both.
    // Row 2: B's entries sit on both sides of A's.
    CSR A = to_csr({{0,0,1},{0,2,2},{2,1,5}}, 3);
    CSR B = to_csr({{0,0,3},{0,1,4},{2,0,6},{2,2,7}}, 3);
    CSR C = add_csr(A, B);

    CHECK(C.n == 3);
    CHECK(C.values  == vector<double>{4, 4, 2, 6, 5, 7});
    CHECK(C.col_idx == vector<int>{0, 1, 2, 0, 1, 2});
    CHECK(C.row_ptr == vector<int>{0, 3, 3, 6});

    // Addition commutes
    CSR D = add_csr(B, A);
    CHECK(D.values  == C.values);
    CHECK(D.col_idx == C.col_idx);
    CHECK(D.row_ptr == C.row_ptr);
}

TEST_CASE("add_csr: adding an empty matrix changes nothing"){
    CSR A = to_csr({{0,2,1},{1,1,3},{0,0,4}}, 3);
    CSR C = add_csr(A, to_csr({}, 3));

    CHECK(C.values  == A.values);
    CHECK(C.col_idx == A.col_idx);
    CHECK(C.row_ptr == A.row_ptr);
}

TEST_CASE("add_csr: mismatched sizes throw"){
    CHECK_THROWS_AS(add_csr(to_csr({}, 3), to_csr({}, 4)), std::runtime_error);
}

//     [ 1  2  0  3 ]
// M = [ 2  4  5  0 ]
//     [ 0  5  6  7 ]
//     [ 3  0  7  8 ]

static CSR four_by_four(){
    return to_csr({{0,0,1},{0,1,2},{0,3,3},
                   {1,0,2},{1,1,4},{1,2,5},
                   {2,1,5},{2,2,6},{2,3,7},
                   {3,0,3},{3,2,7},{3,3,8}}, 4);
}

TEST_CASE("submatrix: drop index 1, keep 0, 2, 3"){
    //  [ 1  0  3 ]
    //  [ 0  6  7 ]
    //  [ 3  7  8 ]
    CSR S = extract_principal_submatrix(four_by_four(), {0,-1,1,2});

    CHECK(S.n == 3);
    CHECK(S.values  == vector<double>{1, 3, 6, 7, 3, 7, 8});
    CHECK(S.col_idx == vector<int>{0, 2, 1, 2, 0, 1, 2});
    CHECK(S.row_ptr == vector<int>{0, 2, 4, 7});
}

TEST_CASE("submatrix: the map also renumbers, not only filters"){
    // New 0 = old 2, new 1 = old 3, new 2 = old 0
    //  [ 6  7  0 ]
    //  [ 7  8  3 ]
    //  [ 0  3  1 ]
    CSR S = extract_principal_submatrix(four_by_four(), {2,-1,0,1});

    CHECK(S.n == 3);
    CHECK(S.values  == vector<double>{6, 7, 7, 8, 3, 3, 1});
    CHECK(S.col_idx == vector<int>{0, 1, 0, 1, 2, 1, 2});
    CHECK(S.row_ptr == vector<int>{0, 2, 5, 7});
}

TEST_CASE("submatrix: keep everything gives M back, keep nothing gives 0x0"){
    const CSR M = four_by_four();

    CSR all = extract_principal_submatrix(M, {0,1,2,3});
    CHECK(all.n == 4);
    CHECK(all.values  == M.values);
    CHECK(all.col_idx == M.col_idx);
    CHECK(all.row_ptr == M.row_ptr);

    CSR none = extract_principal_submatrix(M, {-1,-1,-1,-1});
    CHECK(none.n == 0);
    CHECK(none.values.empty());
    CHECK(none.row_ptr == vector<int>{0});
}

TEST_CASE("submatrix: map of the wrong size throws"){
    CHECK_THROWS_AS(extract_principal_submatrix(four_by_four(), {0,1,2}), std::runtime_error);
}
