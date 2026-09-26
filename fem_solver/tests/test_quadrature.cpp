#include "doctest.h"
#include "quadrature.h"

using namespace fem;
using doctest::Approx;

const array<array<double,2>,3> SKEWED_TRI = {{{0.3,0.1},{2.0,0.5},{0.7,1.9}}};

TEST_CASE("quadrature: weights sum to 1"){
    double tri = 0.0, edge = 0.0;
    for(double w : CENTROID.Weights) tri += w;
    for(double w : MIDPOINT.Weights) edge += w;
    CHECK(tri == Approx(1));
    CHECK(edge == Approx(1));
}

TEST_CASE("triangle_quadrature: constant integrates to the area"){
    double I = triangle_quadrature(CENTROID, SKEWED_TRI, [](double, double){ return 1.0; });
    CHECK(I == Approx(trig_area(SKEWED_TRI)));
}

TEST_CASE("triangle_quadrature: CENTROID is exact for linear functions"){
    // ∫_T (2 + 3x - y) = area * (2 + 3 x_c - y_c), x_c the centroid
    const double xc = (SKEWED_TRI[0][0] + SKEWED_TRI[1][0] + SKEWED_TRI[2][0]) / 3;
    const double yc = (SKEWED_TRI[0][1] + SKEWED_TRI[1][1] + SKEWED_TRI[2][1]) / 3;
    double I = triangle_quadrature(CENTROID, SKEWED_TRI, [](double x, double y){ return 2 + 3*x - y; });
    CHECK(I == Approx(trig_area(SKEWED_TRI) * (2 + 3*xc - yc)));
}

TEST_CASE("edge_quadrature: constant integrates to the length"){
    array<array<double,2>,2> E = {{{0,0},{3,4}}};
    CHECK(edge_quadrature(MIDPOINT, E, [](double, double){ return 1.0; }) == Approx(5));
}

TEST_CASE("edge_quadrature: MIDPOINT is exact for linear functions"){
    // x runs 0 -> 3 along a length-5 edge: ∫ x ds = 5 * 1.5
    array<array<double,2>,2> E = {{{0,0},{3,4}}};
    CHECK(edge_quadrature(MIDPOINT, E, [](double x, double){ return x; }) == Approx(7.5));
}
