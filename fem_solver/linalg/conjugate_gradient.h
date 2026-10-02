#pragma once

#include "vector_ops.h"
#include <sstream>
namespace fem{
    
    inline vector<double> conjugate_gradient_solve(const CSR& lhs, 
                                            const vector<double>& rhs,
                                            const vector<double>& initial_guess, 
                                            double tolerance,
                                            int CG_MAX_ITERATIONS)
    {
        vector<double> x = initial_guess.empty() ? zeros(lhs.n) : initial_guess;
        vector<double> r = rhs; // r = b; 
        vector<double> z = zeros(lhs.n);
        vector<double> inv_diag = inverse_diagonal(lhs);

        // initial residual calculation

        vector<double> tmp = zeros(lhs.n);
        spmv(lhs,x,tmp);            // tmp = Ax0
        axpy(-1,tmp,r);             // r = b - Ax0
        apply_jacobi(inv_diag,r,z);      // z = preconditioner(b-Ax0)

        // Loop setup

        vector<double> p = z;
        double initial_error = norm2(rhs);

        if(norm2(r) <= tolerance * initial_error) return x; 
        
        double a; double beta; double rz_old = dot(r,z);
        vector<double> t = zeros(lhs.n);

        for(int m = 1; m <= CG_MAX_ITERATIONS; ++m){
            spmv(lhs,p,t);                      // t[m] = Ap[m]
            a = rz_old / dot(p,t);              // a[m] = r[m-1]^Tz[m-1]/(p[m]^Tt[m])
            axpy(a,p,x);                        // x[m] = x[m-1] + a[m]p[m]
            axpy(-a,t,r);                       // r[m] = r[m-1] -a[m]t[m]
            if(norm2(r) <= tolerance * initial_error) return x; 
            apply_jacobi(inv_diag,r,z);              // precondition r : z = D^-1 r
            double rz_new = dot(r,z); 
            beta = rz_new / rz_old;           // beta[m+1] = r[m]^Tz[m]/(r[m-1]^Tz[m-1])
            rz_old = rz_new;
            xpby(beta,z,p);                     // p[m+1] = z[m] + beta[m+1]p[m]
        }
        if(norm2(r) <= tolerance * initial_error) return x; 

        std::ostringstream msg; // scientific, to_string would print 1e-12 as 0.000000
        msg << std::scientific << "In conjugate_gradient_solve: no convergence within max iterations, (maxIterations,relativeResidual,tolerance) = ("
            << CG_MAX_ITERATIONS << ", " << norm2(r) / initial_error << ", " << tolerance << ")";
        throw std::runtime_error(msg.str());
    }
} // namespace fem