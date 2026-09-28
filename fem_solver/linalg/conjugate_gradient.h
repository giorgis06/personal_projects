#pragma once

#include "csr.h"
namespace fem{
    inline vector<double> conjugate_gradient_solve(const CSR& rhs, 
                                            const vector<double>& lhs,
                                            const vector<double>& initial_guess, 
                                            double tolerance)
    {
        return {};
    }
} // namespace fem