import numpy as np
import pytest
from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.results.probe import locate


@pytest.fixture
def mesh():
    # unit square split into four triangles around its centre
    nodes = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [0.5, 0.5]], dtype=float)
    triangles = np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]])
    return MeshData(nodes, np.arange(1, 6), triangles, np.empty((0, 2), int), {}, {})


def test_a_point_is_found_in_its_triangle_with_weights_that_rebuild_it(mesh):
    triangle, weights = locate(mesh, 0.5, 0.2)
    assert triangle == 0
    corners = mesh.nodes[mesh.triangles[triangle]]
    np.testing.assert_allclose(weights @ corners, [0.5, 0.2], atol=1e-12)
    assert weights.sum() == pytest.approx(1.0)


def test_a_point_outside_the_mesh_is_not_found(mesh):
    assert locate(mesh, 1.5, 0.5) is None
    assert locate(mesh, -0.01, 0.5) is None


def test_points_on_a_corner_an_edge_and_the_boundary_are_inside(mesh):
    assert locate(mesh, 0.0, 0.0) is not None
    assert locate(mesh, 0.5, 0.5) is not None  # the node every triangle shares
    assert locate(mesh, 1.0, 0.5) is not None  # on the outer edge


def test_a_mesh_without_triangles_finds_nothing():
    empty = MeshData(
        np.zeros((0, 2)), np.zeros(0, int), np.zeros((0, 3), int), np.zeros((0, 2), int), {}, {}
    )
    assert locate(empty, 0.0, 0.0) is None
