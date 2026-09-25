#pragma once

#include <vector>
#include <algorithm>

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

}