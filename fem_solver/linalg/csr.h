#pragma once

#include <vector>
#include <algorithm>
#include <stdexcept>
#include <string> 

namespace fem{

using std::vector;

struct Triplet{
    int Row,Col;
    double Value; 

    bool operator<(const Triplet& t) const{
        if(Row < t.Row || (Row == t.Row && Col < t.Col)) return true;
        else return false;
    }
};

struct CSR{
    int n;
    vector<double> values;
    vector<int> col_idx;
    vector<int> row_ptr;
};

inline CSR to_csr(vector<Triplet> triplets, int n){
    CSR K;
    K.n = n;
    K.row_ptr.assign(n + 1, 0);

    if(triplets.empty()) return K;
    
    std::sort(triplets.begin(),triplets.end());

    // Initialize K. Row_ptr shows position of k-th row in the value matrix (its starting index).
    // Adding an element to the 0th row means the startting point of row 1 has been pushed by 1 to the right.
    

    K.values.push_back(triplets.front().Value);
    K.col_idx.push_back(triplets.front().Col);
    K.row_ptr[triplets.front().Row + 1]++;
    
    for(size_t i = 1; i < triplets.size(); ++i){

        // If the same triplet was calculated by another triangle, add the entry

        if(triplets[i].Row == triplets[i-1].Row && triplets[i].Col == triplets[i-1].Col){
            K.values.back() += triplets[i].Value;
        }
        else{
            K.values.push_back(triplets[i].Value);
            K.col_idx.push_back(triplets[i].Col);
            K.row_ptr[triplets[i].Row + 1]++; // Note a +1 push in the beginning index of row ti.row+1 due to addition of element at row ti.
        }
    }

    // Running sum. The previous indeces now reflect actual starting positions of rows in the values vector

    for(int r = 0; r < n; r++){
        K.row_ptr[r+1] += K.row_ptr[r];
    }

    return K;
}

inline CSR add_csr(const CSR& A, const CSR& B){
    if(A.n != B.n) throw std::runtime_error("In add_csr: Sparse matrices are not of the same dimension, (dimA,dimB) = (" + std::to_string(A.n) + ", " +std::to_string(B.n) +")");    
    vector<Triplet> sum; 
    sum.reserve(A.values.size() + B.values.size());

    for(int i = 0; i < A.n; ++i){
        for(int j = A.row_ptr[i]; j < A.row_ptr[i+1]; ++j){
            sum.push_back({i,A.col_idx[j],A.values[j]});
        }
        for(int j = B.row_ptr[i]; j < B.row_ptr[i+1]; ++j){
            sum.push_back({i,B.col_idx[j],B.values[j]});
        }
    }

    // SLOW VARIANT, SORTS AGAIN O(nnz*lognnz) , CHANGE FOR TIME VARYING

    return to_csr(std::move(sum),A.n);
}


inline CSR extract_principal_submatrix(const CSR& A, 
                                       const vector<int>& map,
                                       int dim_submatrix){
    if(map.size() != static_cast<size_t>(A.n)) throw std::runtime_error("In extract_principal_submatrix: index map and matrix are not of the same dimension, (dimMap,dimA) = (" + std::to_string(map.size()) + ", " + std::to_string(A.n) + ")");
    vector<Triplet> triplets;

    // map[i] == -1 -> index is red, map[i] != -1 index is green
    // this function creates a submatrix which contains only green-green elements

    for(int r = 0; r < A.n; ++r){
        for(int j = A.row_ptr[r]; j < A.row_ptr[r+1]; ++j){
            if(map[r] != -1 && map[A.col_idx[j]] != -1) triplets.push_back({map[r],map[A.col_idx[j]],A.values[j]});
        }
    }
    return to_csr(std::move(triplets),dim_submatrix);
}

// ---- Vector kernels ----------------------------------------------------------
// All in place: they write into a vector the caller already allocated, so a solver loop
// allocates nothing. Same shape as cuSPARSE / cuBLAS (SpMV, axpy, dot), for the GPU port.

inline void spmv(const CSR& A, const vector<double>& x, vector<double>& y){
    // y = A x
    if(x.size() != static_cast<size_t>(A.n) || y.size() != static_cast<size_t>(A.n)) throw std::runtime_error("In spmv: matrix and vectors are not of the same dimension, (dimA,dimX,dimY) = (" + std::to_string(A.n) + ", " + std::to_string(x.size()) + ", " + std::to_string(y.size()) + ")");

    #pragma omp parallel for
    for(int r = 0; r < A.n; r++){
        double sum = 0.0;
        for(int j = A.row_ptr[r]; j < A.row_ptr[r+1]; ++j){
            sum += A.values[j]*x[A.col_idx[j]];
        }
        y[r] = sum;
    }
}

inline void axpy(double a, const vector<double>& x, vector<double>& y){
    // y += a x
    if(x.size() != y.size()) throw std::runtime_error("In axpy: vectors are not of the same dimension, (dimX,dimY) = (" + std::to_string(x.size()) + ", " + std::to_string(y.size()) + ")");
    for(size_t i = 0; i < x.size(); ++i) y[i] += a*x[i];
}

inline double dot(const vector<double>& x, const vector<double>& y){
    if(x.size() != y.size()) throw std::runtime_error("In dot: vectors are not of the same dimension, (dimX,dimY) = (" + std::to_string(x.size()) + ", " + std::to_string(y.size()) + ")");
    double sum = 0.0;
    for(size_t i = 0; i < x.size(); ++i) sum += x[i]*y[i];
    return sum;
}

inline vector<double> extract_principal_subvector(const vector<double>& v, const vector<int>& map, int dim_subvec){
    if(map.size() != v.size()) throw std::runtime_error("In extract_principal_subvector: index map and vector are not of the same dimension, (dimMap,dimV) = (" + std::to_string(map.size()) + ", " + std::to_string(v.size()) + ")");
    vector<double> result(dim_subvec,0.0);
    // map[i] == -1 -> index is red, map[i] != -1 index is green
    // this function creates a subvector which contains only green-indexed elements
    for(size_t i = 0; i < v.size(); ++i){
        if(map[i] == - 1) continue; 
        else result[map[i]] = v[i]; 
    }
    return result;
}

} // namespace fem