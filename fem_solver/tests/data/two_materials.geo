// [0,2] x [0,1] split at x = 1 into two regions sharing one line (the interface).
h = 0.25;

Point(1) = {0, 0, 0, h};
Point(2) = {1, 0, 0, h};
Point(3) = {2, 0, 0, h};
Point(4) = {2, 1, 0, h};
Point(5) = {1, 1, 0, h};
Point(6) = {0, 1, 0, h};

Line(1) = {1, 2};
Line(2) = {2, 3};
Line(3) = {3, 4};
Line(4) = {4, 5};
Line(5) = {5, 6};
Line(6) = {6, 1};
Line(7) = {2, 5};   // interface

Curve Loop(1) = {1, 7, 5, 6};
Plane Surface(1) = {1};
Curve Loop(2) = {2, 3, 4, -7};
Plane Surface(2) = {2};

Physical Curve("outer", 1)     = {1, 2, 3, 4, 5, 6};
Physical Curve("interface", 2) = {7};
Physical Surface("glass", 10)  = {1};
Physical Surface("air", 11)    = {2};
