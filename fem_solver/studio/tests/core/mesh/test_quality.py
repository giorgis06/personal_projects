import numpy as np
import pytest
from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.mesh.quality import quality, signed_areas


def mesh_of(nodes, triangles) -> MeshData:
    nodes = np.array(nodes, dtype=float)
    return MeshData(
        nodes=nodes,
        node_tags=np.arange(1, len(nodes) + 1),
        triangles=np.array(triangles),
        edges=np.empty((0, 2), dtype=int),
        regions={},
        boundaries={},
    )


def test_right_isosceles_triangle():
    stats = quality(mesh_of([[0, 0], [1, 0], [0, 1]], [[0, 1, 2]]))
    assert stats.total_area == pytest.approx(0.5)
    assert stats.min_angle == pytest.approx(45.0)
    assert stats.max_edge == pytest.approx(2**0.5)
    assert stats.n_inverted == 0


def test_clockwise_triangle_is_counted_and_has_negative_area():
    mesh = mesh_of([[0, 0], [1, 0], [0, 1]], [[0, 2, 1]])
    assert signed_areas(mesh)[0] == pytest.approx(-0.5)
    assert quality(mesh).n_inverted == 1


def test_equilateral_triangle_angle():
    stats = quality(mesh_of([[0, 0], [1, 0], [0.5, 3**0.5 / 2]], [[0, 1, 2]]))
    assert stats.min_angle == pytest.approx(60.0)
