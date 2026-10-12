import gmsh
import meshio
import numpy as np
import pytest
from examples.capacitor import capacitor_scene
from femstudio.core.mesh.mesher import MeshError, mesh_scene
from femstudio.core.mesh.quality import quality
from femstudio.core.scene.boundary import Between, Outline, Side
from femstudio.core.scene.shapes import Circle, Rectangle
from tests.core.mesh.helpers import boundary, edge_length, edge_nodes, region, region_area, scene

PI = np.pi


@pytest.fixture(scope="module")
def capacitor(tmp_path_factory):
    path = tmp_path_factory.mktemp("cap") / "capacitor.msh"
    logs: list[str] = []
    mesh = mesh_scene(capacitor_scene(), 0.05, path, logs.append)
    return mesh, path, logs


def test_capacitor_physical_names_match_the_scene(capacitor):
    _, path, _ = capacitor
    names = meshio.read(path).field_data
    assert {name: int(dim) for name, (_, dim) in names.items()} == {
        "glass": 2,
        "air": 2,
        "inner_electrode": 1,
        "outer_wall": 1,
    }


def test_capacitor_region_areas(capacitor):
    mesh, _, _ = capacitor
    # exact annulus areas; a polygonal mesh is a little smaller
    assert region_area(mesh, "glass") == pytest.approx(PI * (0.5**2 - 0.2**2), rel=1e-2)
    assert region_area(mesh, "air") == pytest.approx(PI * (2.0**2 - 0.5**2), rel=1e-2)


def test_capacitor_boundary_nodes_lie_on_their_circles(capacitor):
    mesh, _, _ = capacitor
    for name, radius in [("inner_electrode", 0.2), ("outer_wall", 2.0)]:
        r = np.linalg.norm(edge_nodes(mesh, name), axis=1)
        assert np.abs(r - radius).max() < 1e-9
        assert edge_length(mesh, name) == pytest.approx(2 * PI * radius, rel=1e-2)


def test_capacitor_regions_partition_the_triangles(capacitor):
    mesh, _, _ = capacitor
    owned = np.concatenate([mesh.regions["glass"], mesh.regions["air"]])
    assert np.array_equal(np.sort(owned), np.arange(mesh.n_triangles))


def test_capacitor_mesh_is_counter_clockwise_and_well_formed(capacitor):
    mesh, _, _ = capacitor
    stats = quality(mesh)
    assert stats.n_inverted == 0
    assert stats.min_angle > 20.0
    assert len(np.unique(mesh.node_tags)) == mesh.n_nodes


def test_gmsh_log_is_forwarded_and_gmsh_is_released(capacitor):
    _, _, logs = capacitor
    assert any("Meshing" in line for line in logs)
    assert not gmsh.isInitialized()


def test_unit_square_sides_are_picked_by_name(tmp_path):
    square = Rectangle("sq", (0.0, 0.0), 1.0, 1.0)
    sides = ["bottom", "right", "top", "left"]
    s = scene([square], [region("air", square)], [boundary(n, Side("sq", n)) for n in sides])
    mesh = mesh_scene(s, 0.25, tmp_path / "sq.msh")
    assert region_area(mesh, "air") == pytest.approx(1.0, abs=1e-12)
    expected = {"bottom": ("y", 0.0), "right": ("x", 1.0), "top": ("y", 1.0), "left": ("x", 0.0)}
    for name, (axis, value) in expected.items():
        nodes = edge_nodes(mesh, name)
        assert np.abs(nodes[:, 0 if axis == "x" else 1] - value).max() < 1e-12
        assert edge_length(mesh, name) == pytest.approx(1.0, abs=1e-12)


def test_between_two_touching_rectangles_is_their_shared_edge(tmp_path):
    left = Rectangle("left_rect", (0.0, 0.0), 1.0, 1.0)
    right = Rectangle("right_rect", (1.0, 0.0), 1.0, 1.0)
    s = scene(
        [left, right],
        [region("glass", left), region("air", right)],
        [
            boundary("interface", Between("glass", "air")),
            boundary("far", Side("right_rect", "right")),
        ],
    )
    mesh = mesh_scene(s, 0.25, tmp_path / "two.msh")
    assert region_area(mesh, "glass") == pytest.approx(1.0, abs=1e-12)
    assert region_area(mesh, "air") == pytest.approx(1.0, abs=1e-12)
    assert np.abs(edge_nodes(mesh, "interface")[:, 0] - 1.0).max() < 1e-12
    assert edge_length(mesh, "interface") == pytest.approx(1.0, abs=1e-12)
    assert np.abs(edge_nodes(mesh, "far")[:, 0] - 2.0).max() < 1e-12


def test_interior_outline_becomes_a_named_curve_inside_a_region(tmp_path):
    disk = Circle("disk", (0.0, 0.0), 2.0)
    ring = Circle("ring", (0.0, 0.0), 1.0)
    s = scene([disk, ring], [region("air", disk)], [boundary("charged", Outline("ring"))])
    mesh = mesh_scene(s, 0.1, tmp_path / "ring.msh")
    assert region_area(mesh, "air") == pytest.approx(PI * 4.0, rel=1e-2)
    radii = np.linalg.norm(edge_nodes(mesh, "charged"), axis=1)
    assert np.abs(radii - 1.0).max() < 1e-9
    assert edge_length(mesh, "charged") == pytest.approx(2 * PI, rel=1e-2)


def test_interior_side_is_embedded_as_an_open_segment(tmp_path):
    plate = Rectangle("plate", (0.0, 0.0), 4.0, 4.0)
    ghost = Rectangle("ghost", (1.0, 1.0), 1.0, 1.0)
    s = scene([plate, ghost], [region("air", plate)], [boundary("wire", Side("ghost", "top"))])
    mesh = mesh_scene(s, 0.25, tmp_path / "wire.msh")
    nodes = edge_nodes(mesh, "wire")
    assert np.abs(nodes[:, 1] - 2.0).max() < 1e-12
    assert nodes[:, 0].min() == pytest.approx(1.0) and nodes[:, 0].max() == pytest.approx(2.0)
    assert edge_length(mesh, "wire") == pytest.approx(1.0, abs=1e-12)
    assert region_area(mesh, "air") == pytest.approx(16.0, abs=1e-9)


def test_invalid_scene_is_refused_with_the_finding(tmp_path):
    disk = Circle("disk", (0.0, 0.0), 1.0)
    s = scene([disk], [region("air", disk), region("air", disk)])
    with pytest.raises(MeshError, match="region 'air'.*not unique"):
        mesh_scene(s, 0.2, tmp_path / "x.msh")


@pytest.mark.parametrize("size", [0.0, -1.0])
def test_size_must_be_positive(tmp_path, size):
    disk = Circle("disk", (0.0, 0.0), 1.0)
    with pytest.raises(MeshError, match="size"):
        mesh_scene(scene([disk], [region("air", disk)]), size, tmp_path / "x.msh")


def test_scene_without_regions_is_refused(tmp_path):
    with pytest.raises(MeshError, match="no regions"):
        mesh_scene(scene([], []), 0.2, tmp_path / "x.msh")


def test_empty_region_is_named(tmp_path):
    a = Circle("a", (0.0, 0.0), 1.0)
    b = Circle("b", (5.0, 0.0), 1.0)
    s = scene([a, b], [region("nothing", a & b)])
    with pytest.raises(MeshError, match="region 'nothing' is empty"):
        mesh_scene(s, 0.2, tmp_path / "x.msh")


def test_overlapping_regions_are_refused(tmp_path):
    a = Circle("a", (0.0, 0.0), 1.0)
    b = Circle("b", (0.5, 0.0), 1.0)
    s = scene([a, b], [region("first", a), region("second", b)])
    with pytest.raises(MeshError, match="'first' and 'second' overlap"):
        mesh_scene(s, 0.2, tmp_path / "x.msh")


def test_boundary_outside_every_region_is_refused(tmp_path):
    disk = Circle("disk", (0.0, 0.0), 1.0)
    far = Circle("far", (10.0, 0.0), 1.0)
    s = scene([disk, far], [region("air", disk)], [boundary("stray", Outline("far"))])
    with pytest.raises(MeshError, match="boundary 'stray' lies outside every region"):
        mesh_scene(s, 0.2, tmp_path / "x.msh")


def test_between_regions_that_do_not_touch_is_refused(tmp_path):
    a = Circle("a", (0.0, 0.0), 1.0)
    b = Circle("b", (5.0, 0.0), 1.0)
    s = scene(
        [a, b], [region("one", a), region("two", b)], [boundary("gap", Between("one", "two"))]
    )
    with pytest.raises(MeshError, match="boundary 'gap' matches no curve"):
        mesh_scene(s, 0.2, tmp_path / "x.msh")
