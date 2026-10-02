#pragma once

#include "csr.h"
#include <cmath>

namespace fem{

// Vector operations
// all in place: they write into a vector the caller already allocated, so a solver loop
// allocates nothing. Same shape as cuSPARSE / cuBLAS (SpMV, axpy, dot), for the GPU port

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

inline vector<double> zeros(int n){
    return vector<double>(n,0.0);
}

inline double norm2(const vector<double>& v){
    return std::sqrt(dot(v,v));
}

inline void xpby(double b, const vector<double>& x, vector<double>& y){
    if(x.size() != y.size()) throw std::runtime_error("In xpby: vectors are not of the same dimension, (dimX,dimY) = (" + std::to_string(x.size()) + ", " + std::to_string(y.size()) + ")");
    for(size_t i = 0; i < x.size(); ++i) y[i] = x[i] + b * y[i];
}

} // namespace fem
