import numpy as np
import pytest
from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.results.field import Field
from femstudio.core.results.result_set import ResultSet


@pytest.fixture
def mesh():
    nodes = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [0.5, 0.5]], dtype=float)
    triangles = np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]])
    return MeshData(nodes, np.arange(1, 6), triangles, np.empty((0, 2), int), {}, {})


@pytest.fixture
def results(mesh):
    u = 3.0 * mesh.nodes[:, 0] + 2.0 * mesh.nodes[:, 1]
    fields = {
        "u": Field("u", u, "V", "node"),
        "E": Field("E", np.tile([-3.0, -4.0], (4, 1)), "V/m", "triangle"),
        "w": Field("w", np.array([1.0, 2.0, 3.0, 4.0]), "J/m^3", "triangle"),
    }
    return ResultSet(3, mesh, fields, {"u": "Potential", "E": "Electric field"})


def test_names_keep_their_order_and_labels_fall_back_to_the_name(results):
    assert results.names() == ["u", "E", "w"]
    assert results.label("u") == "Potential"
    assert results.label("w") == "w"
    assert results.unit("E") == "V/m"


def test_a_vector_field_is_shown_by_its_magnitude(results):
    np.testing.assert_allclose(results.scalars("E"), [5.0] * 4)
    assert results.value_range("E") == (5.0, 5.0)


def test_node_values_of_a_nodal_field_are_the_field(results):
    np.testing.assert_array_equal(results.node_values("u"), results.scalars("u"))


def test_node_values_of_a_triangle_field_average_the_triangles_around_a_node(results):
    values = results.node_values("w")
    assert values[4] == pytest.approx(2.5)  # all four triangles, equal areas
    assert values[0] == pytest.approx(2.5)  # triangles 0 and 3 are equal-area: (1 + 4) / 2
    assert values[1] == pytest.approx(1.5)  # triangles 0 and 1


def test_value_range_skips_values_that_are_not_finite(mesh):
    fields = {"u": Field("u", np.array([1.0, np.nan, 5.0, -2.0, np.inf]), "V", "node")}
    assert ResultSet(1, mesh, fields, {}).value_range("u") == (-2.0, 5.0)


def test_value_range_of_nothing_finite_is_zero(mesh):
    fields = {"u": Field("u", np.full(5, np.nan), "V", "node")}
    assert ResultSet(1, mesh, fields, {}).value_range("u") == (0.0, 0.0)


def test_reading_a_nodal_field_interpolates_linearly(results):
    reading = results.reading("u", 0.5, 0.2)
    assert reading.value == pytest.approx(3.0 * 0.5 + 2.0 * 0.2)
    assert reading.triangle == 0
    assert reading.components is None


def test_reading_a_triangle_field_gives_the_triangles_value(results):
    assert results.reading("w", 0.5, 0.2).value == 1.0
    assert results.reading("w", 0.5, 0.8).value == 3.0


def test_reading_a_vector_gives_magnitude_and_components(results):
    reading = results.reading("E", 0.5, 0.2)
    assert reading.value == pytest.approx(5.0)
    assert reading.components == (-3.0, -4.0)


def test_reading_outside_the_mesh_is_none(results):
    assert results.reading("u", 2.0, 2.0) is None
