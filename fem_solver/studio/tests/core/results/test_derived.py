import numpy as np
import pytest
from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.results.derived import (
    energy_density,
    gradient,
    magnitude,
    tensor_per_triangle,
)


@pytest.fixture
def mesh():
    # unit square split into four triangles around its centre; two regions
    nodes = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [0.5, 0.5]], dtype=float)
    triangles = np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]])
    return MeshData(
        nodes=nodes,
        node_tags=np.arange(1, 6),
        triangles=triangles,
        edges=np.empty((0, 2), dtype=int),
        regions={"low": np.array([0, 1]), "high": np.array([2, 3])},
        boundaries={},
    )


def test_gradient_of_a_linear_field_is_exact_on_every_triangle(mesh):
    u = 3.0 * mesh.nodes[:, 0] + 2.0 * mesh.nodes[:, 1] + 1.0
    np.testing.assert_allclose(gradient(mesh, u), np.tile([3.0, 2.0], (4, 1)), atol=1e-12)


def test_gradient_of_a_constant_is_zero(mesh):
    np.testing.assert_allclose(gradient(mesh, np.full(5, 7.0)), 0.0, atol=1e-12)


def test_magnitude():
    np.testing.assert_allclose(magnitude(np.array([[3.0, 4.0], [0.0, -2.0]])), [5.0, 2.0])


def test_tensor_per_triangle_takes_numbers_and_matrices(mesh):
    tensors = tensor_per_triangle(mesh, {"low": 4.0, "high": ((2.0, 0.5), (0.5, 1.0))})
    np.testing.assert_array_equal(tensors[0], [[4.0, 0.0], [0.0, 4.0]])
    np.testing.assert_array_equal(tensors[3], [[2.0, 0.5], [0.5, 1.0]])


def test_triangles_in_no_listed_region_are_nan(mesh):
    tensors = tensor_per_triangle(mesh, {"low": 1.0})
    assert np.isnan(tensors[2:]).all()


def test_energy_density_isotropic():
    # g = (3, 2), |g|^2 = 13: 1/2 * 4 * 13 = 26
    g = np.array([[3.0, 2.0]])
    assert energy_density(g, np.array([4.0 * np.eye(2)]))[0] == pytest.approx(26.0)


def test_energy_density_anisotropic_with_cross_terms_and_scale():
    # A g = (6 + 1, 1.5 + 2) = (7, 3.5); g . A g = 21 + 7 = 28; half of it is 14
    g = np.array([[3.0, 2.0]])
    a = np.array([[[2.0, 0.5], [0.5, 1.0]]])
    assert energy_density(g, a)[0] == pytest.approx(14.0)
    assert energy_density(g, a, scale=1e-3)[0] == pytest.approx(14.0e-3)
