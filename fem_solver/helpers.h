#pragma once

#include <array>
using std::array;

inline double trig_area(const array<double,2>& n1, const array<double,2>& n2, const array<double,2>& n3){
    return 0.5*((n2[0]-n1[0])*(n3[1]-n1[1]) - (n3[0]-n1[0])*(n2[1]-n1[1]));
}