import math

import pytest
from femstudio.core.scene.shapes import Circle, Polygon, Rectangle


def test_circle_outline_is_on_the_circle_and_closed():
    points = Circle("c", (1.0, -2.0), 3.0).outline_points(64)
    assert len(points) == 65 and points[0] == pytest.approx(points[-1])
    assert all(math.hypot(x - 1.0, y + 2.0) == pytest.approx(3.0) for x, y in points)


def test_circle_bounds():
    low, high = Circle("c", (1.0, -2.0), 3.0).bounds
    assert low == pytest.approx((-2.0, -5.0)) and high == pytest.approx((4.0, 1.0))


def test_rectangle_outline_and_bounds():
    rectangle = Rectangle("r", (1.0, 2.0), 3.0, 4.0)
    assert rectangle.outline_points() == ((1, 2), (4, 2), (4, 6), (1, 6), (1, 2))
    assert rectangle.bounds == ((1.0, 2.0), (4.0, 6.0))


def test_rectangle_points_are_counter_clockwise_and_match_the_side_order():
    rectangle = Rectangle("r", (0.0, 0.0), 2.0, 1.0)
    assert rectangle.points == ((0, 0), (2, 0), (2, 1), (0, 1))
    assert rectangle.sides == ("bottom", "right", "top", "left")


def test_polygon_outline_closes_back_to_the_first_point():
    polygon = Polygon("p", ((0.0, 0.0), (2.0, 0.0), (1.0, 3.0)))
    assert polygon.outline_points()[-1] == (0.0, 0.0)
    assert polygon.bounds == ((0.0, 0.0), (2.0, 3.0))
