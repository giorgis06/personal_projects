import gmsh
import meshio
import numpy as np
import pytest
from examples.capacitor import capacitor_scene
from femstudio.core.mesh.mesher import MeshError, mesh_scene
from femstudio.core.mesh.quality import quality
from femstudio.core.scene.boundary import DEFAULT_BOUNDARY_NAME, Between, Outline, Side
from femstudio.core.scene.shapes import Circle, Polygon, Rectangle
from tests.core.mesh.helpers import (
    ZERO,
    boundary,
    edge_length,
    edge_nodes,
    region,
    region_area,
    scene,
)

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
        default=ZERO,
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
    s = scene([disk, ring], [region("air", disk)], [boundary("charged", Outline("ring"))], ZERO)
    mesh = mesh_scene(s, 0.1, tmp_path / "ring.msh")
    assert region_area(mesh, "air") == pytest.approx(PI * 4.0, rel=1e-2)
    radii = np.linalg.norm(edge_nodes(mesh, "charged"), axis=1)
    assert np.abs(radii - 1.0).max() < 1e-9
    assert edge_length(mesh, "charged") == pytest.approx(2 * PI, rel=1e-2)


def test_interior_side_is_embedded_as_an_open_segment(tmp_path):
    plate = Rectangle("plate", (0.0, 0.0), 4.0, 4.0)
    ghost = Rectangle("ghost", (1.0, 1.0), 1.0, 1.0)
    s = scene(
        [plate, ghost], [region("air", plate)], [boundary("wire", Side("ghost", "top"))], ZERO
    )
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


def test_between_regions_that_are_not_neighbours_is_refused(tmp_path):
    cells = [Rectangle(n, (float(i), 0.0), 1.0, 1.0) for i, n in enumerate(["a", "c", "b"])]
    s = scene(
        cells,
        [region(c.name, c) for c in cells],
        [boundary("gap", Between("a", "b"))],
        default=ZERO,
    )
    with pytest.raises(MeshError, match="boundary 'gap' matches no curve"):
        mesh_scene(s, 0.25, tmp_path / "x.msh")


def test_disconnected_regions_are_refused_like_the_solver_does(tmp_path):
    a = Circle("a", (0.0, 0.0), 1.0)
    b = Circle("b", (5.0, 0.0), 1.0)
    s = scene([a, b], [region("one", a), region("two", b)], default=ZERO)
    with pytest.raises(MeshError, match="one connected piece"):
        mesh_scene(s, 0.3, tmp_path / "x.msh")


def test_one_region_with_no_boundaries_owns_every_triangle(tmp_path):
    square = Rectangle("sq", (0.0, 0.0), 1.0, 1.0)
    s = scene([square], [region("air", square)], default=ZERO)
    mesh = mesh_scene(s, 0.25, tmp_path / "a.msh")
    assert len(mesh.regions["air"]) == mesh.n_triangles
    assert region_area(mesh, "air") == pytest.approx(1.0, abs=1e-12)


def test_unnamed_outer_edges_are_refused_without_a_default(tmp_path):
    square = Rectangle("sq", (0.0, 0.0), 1.0, 1.0)
    s = scene([square], [region("air", square)], [boundary("bottom", Side("sq", "bottom"))])
    with pytest.raises(MeshError, match=r"3 outer curve\(s\) are named by no boundary"):
        mesh_scene(s, 0.25, tmp_path / "a.msh")


def test_default_boundary_names_exactly_the_leftover_outer_edges(tmp_path):
    square = Rectangle("sq", (0.0, 0.0), 1.0, 1.0)
    bottom = boundary("bottom", Side("sq", "bottom"))
    s = scene([square], [region("air", square)], [bottom], default=ZERO)
    path = tmp_path / "a.msh"
    mesh = mesh_scene(s, 0.25, path)
    leftover = edge_nodes(mesh, DEFAULT_BOUNDARY_NAME)
    assert edge_length(mesh, DEFAULT_BOUNDARY_NAME) == pytest.approx(3.0, abs=1e-12)
    assert not set(mesh.boundaries["bottom"]) & set(mesh.boundaries[DEFAULT_BOUNDARY_NAME])
    assert leftover[:, 1].max() == pytest.approx(1.0)
    assert DEFAULT_BOUNDARY_NAME in meshio.read(path).field_data


def test_a_boundary_crossing_the_domain_edge_keeps_its_inside_part(tmp_path):
    square = Rectangle("sq", (0.0, 0.0), 1.0, 1.0)
    notch = Circle("notch", (0.5, 0.0), 0.3)
    s = scene(
        [square, notch],
        [region("air", square - notch)],
        [boundary("cut", Outline("notch"))],
        default=ZERO,
    )
    mesh = mesh_scene(s, 0.05, tmp_path / "a.msh")
    r = np.linalg.norm(edge_nodes(mesh, "cut") - [0.5, 0.0], axis=1)
    assert np.abs(r - 0.3).max() < 1e-9
    assert edge_length(mesh, "cut") == pytest.approx(PI * 0.3, rel=2e-2)


def test_a_side_crossing_into_an_intersection_keeps_its_inside_part(tmp_path):
    square = Rectangle("sq", (0.0, 0.0), 1.0, 1.0)
    strip = Rectangle("strip", (0.25, -1.0), 0.5, 3.0)
    s = scene(
        [square, strip],
        [region("air", square & strip)],
        [boundary("floor", Side("sq", "bottom"))],
        default=ZERO,
    )
    mesh = mesh_scene(s, 0.1, tmp_path / "a.msh")
    assert edge_length(mesh, "floor") == pytest.approx(0.5, abs=1e-12)


def test_two_boundaries_may_not_name_the_same_curve(tmp_path):
    square = Rectangle("sq", (0.0, 0.0), 1.0, 1.0)
    s = scene(
        [square],
        [region("air", square)],
        [boundary("all", Outline("sq")), boundary("floor", Side("sq", "bottom"))],
    )
    with pytest.raises(MeshError, match="'all' and 'floor' both name the same curve"):
        mesh_scene(s, 0.25, tmp_path / "a.msh")


def test_gmsh_failures_surface_as_mesh_error(tmp_path):
    sliver = Rectangle("sliver", (0.0, 0.0), 1e-9, 1.0)
    s = scene([sliver], [region("air", sliver)], default=ZERO)
    with pytest.raises(MeshError):
        mesh_scene(s, 0.25, tmp_path / "a.msh")


def test_clockwise_polygon_meshes_counter_clockwise(tmp_path):
    points = ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0))
    poly = Polygon("cw", points)
    mesh = mesh_scene(scene([poly], [region("air", poly)], default=ZERO), 0.25, tmp_path / "a.msh")
    assert quality(mesh).n_inverted == 0
    assert region_area(mesh, "air") == pytest.approx(1.0, abs=1e-12)


def test_polygon_sides_follow_the_point_order(tmp_path):
    tri = Polygon("tri", ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)))
    sides = {"edge_1": 1.0, "edge_2": 2**0.5, "edge_3": 1.0}
    s = scene([tri], [region("air", tri)], [boundary(n, Side("tri", n)) for n in sides])
    mesh = mesh_scene(s, 0.2, tmp_path / "a.msh")
    for name, length in sides.items():
        assert edge_length(mesh, name) == pytest.approx(length, abs=1e-12)
    assert np.abs(edge_nodes(mesh, "edge_2").sum(axis=1) - 1.0).max() < 1e-12


def test_callers_gmsh_session_is_left_as_it_was(tmp_path):
    gmsh.initialize()
    try:
        gmsh.model.add("mine")
        gmsh.option.setNumber("Mesh.MeshSizeMax", 9.0)
        gmsh.option.setNumber("General.Terminal", 1)
        square = Rectangle("sq", (0.0, 0.0), 1.0, 1.0)
        s = scene([square], [region("air", square)], default=ZERO)
        mesh_scene(s, 0.25, tmp_path / "a.msh")
        assert gmsh.model.getCurrent() == "mine"
        assert gmsh.model.list() == ["", "mine"]
        assert gmsh.option.getNumber("Mesh.MeshSizeMax") == 9.0
        assert gmsh.option.getNumber("General.Terminal") == 1
    finally:
        gmsh.finalize()
