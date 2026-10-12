import pytest
from examples.capacitor import capacitor_scene
from femstudio.core.scene import editing
from femstudio.core.scene.boundary import Between, Outline, Side
from femstudio.core.scene.editing import EditError
from femstudio.core.scene.operations import leaves
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.shapes import Circle, Polygon, Rectangle
from femstudio.core.scene.validation import validate


@pytest.fixture
def scene():
    return capacitor_scene()


def test_unique_names():
    assert editing.unique_name([], "circle") == "circle"
    assert editing.unique_name(["circle"], "circle") == "circle_2"
    assert editing.unique_name(["circle", "circle_2"], "circle") == "circle_3"


@pytest.mark.parametrize(
    ("kind", "cls"), [("circle", Circle), ("rectangle", Rectangle), ("polygon", Polygon)]
)
def test_new_shapes_have_free_names_and_valid_defaults(scene, kind, cls):
    shape = editing.new_shape(scene, kind)
    assert isinstance(shape, cls)
    editing.add_shape(scene, shape)
    again = editing.new_shape(scene, kind)
    assert again.name == f"{kind}_2"


def test_unknown_shape_kind(scene):
    with pytest.raises(EditError, match="unknown shape kind"):
        editing.new_shape(scene, "star")


def test_add_shape_refuses_taken_and_empty_names(scene):
    with pytest.raises(EditError, match="already exists"):
        editing.add_shape(scene, Circle("wall", (0.0, 0.0), 1.0))
    with pytest.raises(EditError, match="empty"):
        editing.add_shape(scene, Circle("  ", (0.0, 0.0), 1.0))
    with pytest.raises(EditError, match="reserved"):
        editing.add_shape(scene, Circle("default_boundary", (0.0, 0.0), 1.0))
    assert len(scene.shapes) == 3


def test_update_shape_changes_it_in_place_so_regions_follow(scene):
    editing.update_shape(scene, "glass_outer", radius=0.6, center=(0.1, 0.0))
    shape = scene.shape("glass_outer")
    assert (shape.radius, shape.center) == (0.6, (0.1, 0.0))
    assert next(leaves(scene.region("glass").area)) is shape


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"radius": -1.0}, "positive"),
        ({"radius": 0.0}, "positive"),
        ({"radius": float("nan")}, "finite"),
        ({"center": (float("inf"), 0.0)}, "finite"),
        ({"width": 1.0}, "no width"),
    ],
)
def test_update_shape_refuses_bad_values_and_leaves_the_shape(scene, fields, message):
    before = Circle("electrode", (0.0, 0.0), 0.2)
    with pytest.raises(EditError, match=message):
        editing.update_shape(scene, "electrode", **fields)
    assert scene.shape("electrode") == before


def test_update_polygon_points(scene):
    editing.add_shape(scene, Polygon("tri", ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))))
    editing.update_shape(scene, "tri", points=[(0, 0), (2, 0), (2, 2), (0, 2)])
    assert scene.shape("tri").points == ((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0))
    with pytest.raises(EditError, match="three points"):
        editing.update_shape(scene, "tri", points=[(0, 0), (1, 1)])


def test_rename_shape_updates_the_boundaries_that_name_it(scene):
    editing.rename_shape(scene, "wall", "far_wall")
    assert scene.boundary("outer_wall").curve == Outline("far_wall")
    assert [s.name for s in scene.shapes] == ["electrode", "glass_outer", "far_wall"]
    assert validate(scene) == []


def test_rename_shape_refuses_a_taken_name(scene):
    with pytest.raises(EditError, match="already exists"):
        editing.rename_shape(scene, "wall", "electrode")
    assert scene.shapes[2].name == "wall"


def test_renaming_to_the_same_name_is_not_a_clash(scene):
    editing.rename_shape(scene, "wall", "wall")


def test_rename_region_updates_between_boundaries(scene):
    editing.add_boundary(scene, "interface", Between("glass", "air"))
    editing.rename_region(scene, "glass", "quartz")
    assert scene.boundary("interface").curve == Between("quartz", "air")


def test_regions_and_boundaries_share_one_namespace(scene):
    with pytest.raises(EditError, match="region or boundary"):
        editing.rename_region(scene, "air", "outer_wall")
    with pytest.raises(EditError, match="region or boundary"):
        editing.rename_boundary(scene, "outer_wall", "glass")
    editing.rename_boundary(scene, "outer_wall", "ground")
    assert scene.boundaries[1].name == "ground"


def test_a_shape_may_share_a_name_with_a_boundary(scene):
    editing.rename_boundary(scene, "outer_wall", "electrode")
    assert validate(scene) == []


def test_remove_shape_refuses_while_something_uses_it(scene):
    with pytest.raises(EditError) as caught:
        editing.remove_shape(scene, "electrode")
    assert "region 'glass'" in str(caught.value) and "boundary 'inner_electrode'" in str(
        caught.value
    )
    assert len(scene.shapes) == 3


def test_remove_an_unused_shape(scene):
    shape = editing.add_shape(scene, editing.new_shape(scene, "circle"))
    editing.remove_shape(scene, shape.name)
    assert [s.name for s in scene.shapes] == ["electrode", "glass_outer", "wall"]


def test_remove_region_refuses_while_a_between_boundary_uses_it(scene):
    editing.add_boundary(scene, "interface", Between("glass", "air"))
    with pytest.raises(EditError, match="boundary 'interface'"):
        editing.remove_region(scene, "glass")
    editing.remove_boundary(scene, "interface")
    editing.remove_region(scene, "glass")
    assert [r.name for r in scene.regions] == ["air"]


def test_area_is_folded_left_to_right(scene):
    area = editing.build_area(
        scene, [(None, "wall"), ("difference", "glass_outer"), ("union", "electrode")]
    )
    assert area == (scene.shape("wall") - scene.shape("glass_outer")) | scene.shape("electrode")


def test_build_area_refuses_unknown_names_and_operations(scene):
    with pytest.raises(EditError, match="no shape named 'ghost'"):
        editing.build_area(scene, [(None, "ghost")])
    with pytest.raises(EditError, match="unknown operation"):
        editing.build_area(scene, [(None, "wall"), ("xor", "electrode")])
    with pytest.raises(EditError, match="at least one"):
        editing.build_area(scene, [])


def test_area_operands_is_the_inverse_of_build_area(scene):
    operands = [(None, "wall"), ("difference", "glass_outer"), ("union", "electrode")]
    assert editing.area_operands(editing.build_area(scene, operands)) == operands
    assert editing.area_operands(scene.shape("wall")) == [(None, "wall")]


def test_area_operands_gives_up_on_a_shape_that_is_not_a_chain(scene):
    nested = scene.shape("wall") - (scene.shape("glass_outer") | scene.shape("electrode"))
    assert editing.area_operands(nested) is None


def test_add_and_change_a_region(scene):
    region = editing.add_region(
        scene, "shell", [(None, "glass_outer"), ("difference", "electrode")]
    )
    assert region.name == "shell" and region.material == {}
    editing.set_region_area(scene, "shell", [(None, "wall")])
    assert scene.region("shell").area is scene.shape("wall")
    with pytest.raises(EditError, match="already exists"):
        editing.add_region(scene, "air", [(None, "wall")])


def test_add_boundary_checks_its_curve(scene):
    editing.add_shape(scene, Rectangle("sq", (0.0, 0.0), 1.0, 1.0))
    editing.add_boundary(scene, "left", Side("sq", "left"))
    with pytest.raises(EditError, match="has no side"):
        editing.add_boundary(scene, "front", Side("sq", "front"))
    with pytest.raises(EditError, match="no shape named"):
        editing.add_boundary(scene, "x", Outline("ghost"))
    with pytest.raises(EditError, match="two different regions"):
        editing.add_boundary(scene, "x", Between("glass", "glass"))
    with pytest.raises(EditError, match="no region named"):
        editing.add_boundary(scene, "x", Between("glass", "vacuum"))


def test_set_boundary_curve(scene):
    editing.set_boundary_curve(scene, "outer_wall", Outline("glass_outer"))
    assert scene.boundary("outer_wall").curve == Outline("glass_outer")
    with pytest.raises(EditError, match="no boundary named"):
        editing.set_boundary_curve(scene, "ghost", Outline("wall"))


def test_the_capacitors_geometry_can_be_built_from_an_empty_scene():
    scene = Scene("electrostatics")
    for name, radius in [("electrode", 0.2), ("glass_outer", 0.5), ("wall", 2.0)]:
        shape = editing.new_shape(scene, "circle")
        shape.name, shape.radius = name, radius
        editing.add_shape(scene, shape)
    editing.add_region(scene, "glass", [(None, "glass_outer"), ("difference", "electrode")])
    editing.add_region(scene, "air", [(None, "wall"), ("difference", "glass_outer")])
    editing.add_boundary(scene, "inner_electrode", Outline("electrode"))
    editing.add_boundary(scene, "outer_wall", Outline("wall"))
    reference = capacitor_scene()
    assert scene.shapes == reference.shapes
    assert [(r.name, r.area) for r in scene.regions] == [
        (r.name, r.area) for r in reference.regions
    ]
    assert [(b.name, b.curve) for b in scene.boundaries] == [
        (b.name, b.curve) for b in reference.boundaries
    ]


def test_a_refused_update_changes_none_of_the_fields(scene):
    editing.add_shape(scene, Rectangle("r", (0.0, 0.0), 1.0, 1.0))
    with pytest.raises(EditError, match="height must be positive"):
        editing.update_shape(scene, "r", width=3.0, height=-1.0)
    assert scene.shape("r") == Rectangle("r", (0.0, 0.0), 1.0, 1.0)


def test_non_numeric_coordinates_are_an_edit_error_not_a_crash(scene):
    editing.add_shape(scene, Polygon("tri", ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))))
    with pytest.raises(EditError, match="points"):
        editing.update_shape(scene, "tri", points=[(0, 0), (1, 0), ("a", 1)])
    with pytest.raises(EditError, match="must be numbers"):
        editing.update_shape(scene, "wall", center=("x", 0.0))
    with pytest.raises(EditError, match="pairs"):
        editing.update_shape(scene, "tri", points=[(0, 0), (1, 0), (1, 2, 3)])
    assert scene.shape("tri").points == ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))
    assert scene.shape("wall").center == (0.0, 0.0)


def test_the_editing_functions_are_public(scene):
    for name in ("add_shape", "update_shape", "rename_shape", "build_area", "add_boundary"):
        assert callable(getattr(editing, name))


@pytest.mark.parametrize(
    ("key", "value"), [("corner", (1.0,)), ("corner", (1.0, 2.0, 3.0)), ("center", ())]
)
def test_a_coordinate_that_is_not_a_pair_is_an_edit_error(scene, key, value):
    editing.add_shape(scene, Rectangle("r", (0.0, 0.0), 1.0, 1.0))
    shape = "r" if key == "corner" else "wall"
    with pytest.raises(EditError, match="must be an \\(x, y\\) pair"):
        editing.update_shape(scene, shape, **{key: value})
    assert scene.shape("r") == Rectangle("r", (0.0, 0.0), 1.0, 1.0)
    assert scene.shape("wall").center == (0.0, 0.0)
