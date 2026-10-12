import pytest
from femstudio.core.scene.operations import Operation, difference, intersection, leaves, union
from femstudio.core.scene.shapes import Circle

A = Circle("a", (0.0, 0.0), 1.0)
B = Circle("b", (0.0, 0.0), 2.0)
C = Circle("c", (1.0, 0.0), 0.5)


def test_operators_build_operations():
    assert A | B == Operation("union", (A, B))
    assert B - A == Operation("difference", (B, A))
    assert A & B == Operation("intersection", (A, B))


def test_functions_match_operators():
    assert union(A, B) == A | B
    assert difference(B, A) == B - A
    assert intersection(A, B) == A & B


def test_chained_operators_nest_to_the_left():
    assert B - A - C == Operation("difference", (Operation("difference", (B, A)), C))


def test_leaves_lists_shapes_in_order():
    assert list(leaves((B - A) | C)) == [B, A, C]


def test_leaves_of_a_plain_shape_is_itself():
    assert list(leaves(A)) == [A]


@pytest.mark.parametrize("build", [union, difference, intersection])
def test_an_operation_needs_two_areas(build):
    with pytest.raises(ValueError):
        build(A)
