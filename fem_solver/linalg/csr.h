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

}