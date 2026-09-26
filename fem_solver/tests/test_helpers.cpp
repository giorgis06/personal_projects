#include "doctest.h"
#include "helpers.h"

using namespace fem;
using doctest::Approx;

// Unit right triangle, counter-clockwise: area 0.5
const array<array<double,2>,3> UNIT_TRI = {{{0,0},{1,0},{0,1}}};

TEST_CASE("trig_area: sign follows winding"){
    CHECK(trig_area(UNIT_TRI) == Approx(0.5));

    array<array<double,2>,3> clockwise = {{UNIT_TRI[0], UNIT_TRI[2], UNIT_TRI[1]}};
    CHECK(trig_area(clockwise) == Approx(-0.5));
}

TEST_CASE("trig_area: translation invariant"){
    array<array<double,2>,3> shifted = {{{10,-3},{11,-3},{10,-2}}};
    CHECK(trig_area(shifted) == Approx(trig_area(UNIT_TRI)));
}

TEST_CASE("hat_gradients: unit right triangle by hand"){
    auto g = hat_gradients(UNIT_TRI);
    // φ0 = 1-x-y, φ1 = x, φ2 = y
    CHECK(g[0][0] == Approx(-1)); CHECK(g[0][1] == Approx(-1));
    CHECK(g[1][0] == Approx( 1)); CHECK(g[1][1] == Approx( 0));
    CHECK(g[2][0] == Approx( 0)); CHECK(g[2][1] == Approx( 1));
}

TEST_CASE("hat_gradients: partition of unity and nodal property on a skewed triangle"){
    array<array<double,2>,3> T = {{{0.3,0.1},{2.0,0.5},{0.7,1.9}}};
    auto g = hat_gradients(T);

    // Σ φ_i = 1 everywhere, so the gradients sum to zero
    CHECK(g[0][0] + g[1][0] + g[2][0] == Approx(0).epsilon(1e-12));
    CHECK(g[0][1] + g[1][1] + g[2][1] == Approx(0).epsilon(1e-12));

    // φ_i is 1 at node i and 0 at node j, and linear: ∇φ_i · (p_j - p_i) = -1
    for(int i = 0; i < 3; ++i){
        for(int j = 0; j < 3; ++j){
            if(i == j) continue;
            array<double,2> d = {T[j][0] - T[i][0], T[j][1] - T[i][1]};
            CHECK(dot_prod_2d(g[i], d) == Approx(-1));
        }
    }
}

TEST_CASE("symmetric_mat_vec: (xx, yy, xy) ordering"){
    array<double,3> a = {2.0, 5.0, 1.0};   // [[2,1],[1,5]]
    auto r = symmetric_mat_vec(a, {3.0, 4.0});
    CHECK(r[0] == Approx(2*3 + 1*4));
    CHECK(r[1] == Approx(1*3 + 5*4));
}

TEST_CASE("dot_prod_2d"){
    CHECK(dot_prod_2d({1.0, 2.0}, {3.0, -4.0}) == Approx(-5));
}
