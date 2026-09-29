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
    CSR S = extract_principal_submatrix(four_by_four(), {0,-1,1,2}, 3);

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
    CSR S = extract_principal_submatrix(four_by_four(), {2,-1,0,1}, 3);

    CHECK(S.n == 3);
    CHECK(S.values  == vector<double>{6, 7, 7, 8, 3, 3, 1});
    CHECK(S.col_idx == vector<int>{0, 1, 0, 1, 2, 1, 2});
    CHECK(S.row_ptr == vector<int>{0, 2, 5, 7});
}

TEST_CASE("submatrix: keep everything gives M back, keep nothing gives 0x0"){
    const CSR M = four_by_four();

    CSR all = extract_principal_submatrix(M, {0,1,2,3}, 4);
    CHECK(all.n == 4);
    CHECK(all.values  == M.values);
    CHECK(all.col_idx == M.col_idx);
    CHECK(all.row_ptr == M.row_ptr);

    CSR none = extract_principal_submatrix(M, {-1,-1,-1,-1}, 0);
    CHECK(none.n == 0);
    CHECK(none.values.empty());
    CHECK(none.row_ptr == vector<int>{0});
}

TEST_CASE("submatrix: map of the wrong size throws"){
    CHECK_THROWS_AS(extract_principal_submatrix(four_by_four(), {0,1,2}, 3), std::runtime_error);
}

TEST_CASE("spmv: matches the dense product"){
    // M x with x = (1, -1, 2, 0.5):
    //   row 0: 1 - 2 + 0 + 1.5 = 0.5
    //   row 1: 2 - 4 + 10 + 0  = 8
    //   row 2: 0 - 5 + 12 + 3.5 = 10.5
    //   row 3: 3 + 0 + 14 + 4  = 21
    // The entries of x differ, so reading x at the wrong index shows.
    vector<double> y(4);
    spmv(four_by_four(), {1, -1, 2, 0.5}, y);
    CHECK(y == vector<double>{0.5, 8, 10.5, 21});
}

TEST_CASE("spmv: empty rows give 0, unit vectors pick out columns"){
    // Only rows 0 and 2 have entries in a 4x4 (same matrix as the to_csr test)
    CSR K = to_csr({{2,2,5},{0,0,1}}, 4);
    vector<double> y(4);
    spmv(K, {1,1,1,1}, y);
    CHECK(y == vector<double>{1, 0, 5, 0});

    // M e_j is column j of M
    const CSR M = four_by_four();
    spmv(M, {0,0,1,0}, y);
    CHECK(y == vector<double>{0, 5, 6, 7});
    spmv(M, {0,0,0,1}, y);
    CHECK(y == vector<double>{3, 0, 7, 8});
}

TEST_CASE("spmv: wrong vector size throws"){
    vector<double> y(4);
    CHECK_THROWS_AS(spmv(four_by_four(), {1, 2, 3}, y), std::runtime_error);
}

TEST_CASE("subvector: keeps the mapped entries at their new positions"){
    // Keep 0, 2, 3 in order
    CHECK(extract_principal_subvector({10, 11, 12, 13}, {0,-1,1,2}, 3) == vector<double>{10, 12, 13});
    // Renumbered: new 0 = old 2, new 1 = old 3, new 2 = old 0
    CHECK(extract_principal_subvector({10, 11, 12, 13}, {2,-1,0,1}, 3) == vector<double>{12, 13, 10});
    // Keep nothing
    CHECK(extract_principal_subvector({10, 11, 12, 13}, {-1,-1,-1,-1}, 0).empty());
}

TEST_CASE("subvector: map of the wrong size throws"){
    CHECK_THROWS_AS(extract_principal_subvector({1, 2, 3}, {0,1}, 2), std::runtime_error);
}

TEST_CASE("in-place spmv overwrites y, doesn't accumulate into it"){
    const CSR M = four_by_four();
    vector<double> y = {100, 100, 100, 100};            // garbage from a previous iteration
    spmv(M, {1, -1, 2, 0.5}, y);
    CHECK(y == vector<double>{0.5, 8, 10.5, 21});
    vector<double> too_short(3);
    CHECK_THROWS_AS(spmv(M, {1, -1, 2, 0.5}, too_short), std::runtime_error);
}

TEST_CASE("axpy and dot"){
    vector<double> y = {1, 2, 3};
    axpy(2.0, {10, 20, 30}, y);
    CHECK(y == vector<double>{21, 42, 63});

    CHECK(dot({1, 2, 3}, {4, 5, 6}) == 32.0);
    CHECK(dot({}, {}) == 0.0);

    CHECK_THROWS_AS(axpy(1.0, {1, 2}, y), std::runtime_error);
    CHECK_THROWS_AS(dot({1, 2}, {1, 2, 3}), std::runtime_error);
}
