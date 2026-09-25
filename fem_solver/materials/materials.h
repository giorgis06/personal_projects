#pragma once

#include <array>
#include <map>

namespace fem{

struct Material{
    std::array<double,3> EPSILON;
    std::array<double,3> MU;
    std::array<double,3> SIGMA;
};

using Materials = std::map<int,Material>;

} //namespace fgem