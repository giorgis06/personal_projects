from pathlib import Path

import numpy as np
import pytest
from femstudio.core.mesh.reader import MeshReadError, read_mesh
from tests.core.mesh.helpers import edge_length, edge_nodes, region_area

DATA = Path(__file__).resolve().parents[4] / "tests" / "data"
SQUARE = ({"air"}, {"bottom", "right", "top", "left"})
EXPECTED = {
    "square.geo": SQUARE,
    "square_h0125.geo": SQUARE,
    "square_h00625.geo": SQUARE,
    "square_h003125.geo": SQUARE,
    "two_materials.geo": ({"glass", "air"}, {"outer", "interface"}),
}


def test_every_fixture_has_an_expectation():
    assert {p.name for p in DATA.glob("*.geo")} == set(EXPECTED)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_geo_fixture_loads_with_its_named_regions_and_edges(name):
    mesh = read_mesh(DATA / name)
    regions, boundaries = EXPECTED[name]
    assert set(mesh.regions) == regions
    assert set(mesh.boundaries) == boundaries
    assert all(len(ids) > 0 for ids in [*mesh.regions.values(), *mesh.boundaries.values()])


@pytest.mark.parametrize("name", ["square.geo", "square_h0125.geo", "square_h003125.geo"])
def test_square_geometry(name):
    mesh = read_mesh(DATA / name)
    assert region_area(mesh, "air") == pytest.approx(1.0, abs=1e-12)
    for side in SQUARE[1]:
        assert edge_length(mesh, side) == pytest.approx(1.0, abs=1e-12)
    assert np.abs(edge_nodes(mesh, "left")[:, 0]).max() < 1e-12


def test_square_edge_count_follows_the_element_size():
    # h = 0.125 divides the unit side into 8 elements
    mesh = read_mesh(DATA / "square_h0125.geo")
    assert len(mesh.boundaries["bottom"]) == 8


def test_two_materials_regions_and_interface():
    mesh = read_mesh(DATA / "two_materials.geo")
    assert region_area(mesh, "glass") == pytest.approx(1.0, abs=1e-12)
    assert region_area(mesh, "air") == pytest.approx(1.0, abs=1e-12)
    assert np.abs(edge_nodes(mesh, "interface")[:, 0] - 1.0).max() < 1e-12
    assert edge_length(mesh, "outer") == pytest.approx(6.0, abs=1e-12)


def test_node_tags_are_one_based_unique_gmsh_tags():
    mesh = read_mesh(DATA / "square.geo")
    assert len(np.unique(mesh.node_tags)) == mesh.n_nodes
    assert mesh.node_tags.min() >= 1


def test_every_node_is_used_and_indices_are_in_range():
    mesh = read_mesh(DATA / "two_materials.geo")
    used = np.unique(np.concatenate([mesh.triangles.ravel(), mesh.edges.ravel()]))
    assert np.array_equal(used, np.arange(mesh.n_nodes))


def test_unnamed_physical_groups_are_skipped(tmp_path):
    path = tmp_path / "plain.geo"
    path.write_text(
        'SetFactory("OpenCASCADE");\nRectangle(1) = {0, 0, 0, 1, 1};\n'
        "Physical Surface(5) = {1};\nMesh.MeshSizeMax = 0.5;\n"
    )
    mesh = read_mesh(path)
    assert mesh.regions == {}
    assert mesh.n_triangles > 0


def test_missing_file(tmp_path):
    with pytest.raises(MeshReadError, match="no such file"):
        read_mesh(tmp_path / "gone.msh")


def test_unsupported_extension(tmp_path):
    path = tmp_path / "mesh.vtk"
    path.write_text("")
    with pytest.raises(MeshReadError, match="unsupported"):
        read_mesh(path)


def test_broken_geo(tmp_path):
    path = tmp_path / "broken.geo"
    path.write_text("Point(1) = {0, 0, ;\n")
    with pytest.raises(MeshReadError):
        read_mesh(path)


def test_geo_without_a_surface_has_no_triangles(tmp_path):
    path = tmp_path / "points.geo"
    path.write_text("Point(1) = {0, 0, 0, 1};\n")
    with pytest.raises(MeshReadError, match="no triangles"):
        read_mesh(path)
