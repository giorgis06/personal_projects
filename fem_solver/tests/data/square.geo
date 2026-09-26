// Unit square, one material, every side tagged separately.
h = 0.25;

Point(1) = {0, 0, 0, h};
Point(2) = {1, 0, 0, h};
Point(3) = {1, 1, 0, h};
Point(4) = {0, 1, 0, h};

Line(1) = {1, 2};
Line(2) = {2, 3};
Line(3) = {3, 4};
Line(4) = {4, 1};

Curve Loop(1) = {1, 2, 3, 4};
Plane Surface(1) = {1};

Physical Curve("bottom", 1) = {1};
Physical Curve("right", 2)  = {2};
Physical Curve("top", 3)    = {3};
Physical Curve("left", 4)   = {4};
Physical Surface("air", 10) = {1};
