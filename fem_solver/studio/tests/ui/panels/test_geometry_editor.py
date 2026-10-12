import numpy as np
import pytest
from examples.capacitor import capacitor_scene
from femstudio.core.scene import editing
from femstudio.core.scene.boundary import Between, Outline, Side
from femstudio.core.scene.shapes import Circle, Polygon, Rectangle
from femstudio.ui.main_window import MainWindow
from tests.ui.conftest import DATA, EXAMPLE

pytestmark = pytest.mark.ui


@pytest.fixture
def window(qtbot, settings):
    window = MainWindow(settings)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


@pytest.fixture
def panel(window):
    return window.properties.panel("Geometry")


@pytest.fixture
def empty(window, panel):
    window.new_scene()
    return window


@pytest.fixture
def opened(window):
    assert window.open_path(EXAMPLE)
    return window


def add_circle(panel, name, radius, center=(0.0, 0.0)):
    panel.add_item("circle")
    panel.field("name").setText(name)
    panel.field("radius").setValue(radius)
    panel.field("center_x").setValue(center[0])
    panel.field("center_y").setValue(center[1])
    panel.apply()


def define_region(panel, name, operands):
    panel.add_item("region")
    panel.field("name").setText(name)
    (_, first), *rest = operands
    panel.field("shape_0").setCurrentText(first)
    for index, (operation, shape) in enumerate(rest, start=1):
        panel.field("add_operand").click()
        panel.field(f"operation_{index}").setCurrentText(operation)
        panel.field(f"shape_{index}").setCurrentText(shape)
    panel.apply()


def define_boundary(panel, name, kind, **targets):
    panel.add_item("boundary")
    panel.field("name").setText(name)
    panel.field("curve_kind").setCurrentText(kind)
    for key, value in targets.items():
        panel.field(key).setCurrentText(value)
    panel.apply()


def test_the_capacitor_is_rebuilt_from_an_empty_scene_in_the_window(empty, panel):
    scene_before = empty.session.scene
    assert scene_before.shapes == [] and empty.document.mesh is None

    add_circle(panel, "electrode", 0.2)
    add_circle(panel, "glass_outer", 0.5)
    add_circle(panel, "wall", 2.0)
    define_region(panel, "glass", [(None, "glass_outer"), ("difference", "electrode")])
    define_region(panel, "air", [(None, "wall"), ("difference", "glass_outer")])
    define_boundary(panel, "inner_electrode", "Outline of a shape", shape="electrode")
    define_boundary(panel, "outer_wall", "Outline of a shape", shape="wall")

    scene = empty.session.scene
    reference = capacitor_scene()
    assert scene.shapes == reference.shapes
    assert [(r.name, r.area) for r in scene.regions] == [
        (r.name, r.area) for r in reference.regions
    ]
    assert [(b.name, b.curve) for b in scene.boundaries] == [
        (b.name, b.curve) for b in reference.boundaries
    ]
    # materials and conditions are the Physics step's job; a new region gets the type's defaults
    assert scene.regions[0].material == {"epsilon": ((1.0, 0.0), (0.0, 1.0))}

    # live preview: the edits meshed the scene, by name
    mesh = empty.document.mesh
    assert mesh is not None and set(mesh.regions) == {"glass", "air"}
    assert set(mesh.boundaries) == {"inner_electrode", "outer_wall"}
    assert empty.status.texts()[0].startswith("Validation: 0 errors")


def test_with_materials_and_conditions_set_the_rebuilt_scene_is_the_capacitor(empty, panel):
    add_circle(panel, "electrode", 0.2)
    add_circle(panel, "glass_outer", 0.5)
    add_circle(panel, "wall", 2.0)
    define_region(panel, "glass", [(None, "glass_outer"), ("difference", "electrode")])
    define_region(panel, "air", [(None, "wall"), ("difference", "glass_outer")])
    define_boundary(panel, "inner_electrode", "Outline of a shape", shape="electrode")
    define_boundary(panel, "outer_wall", "Outline of a shape", shape="wall")
    reference = capacitor_scene()

    def physics(scene):
        for region, source in zip(scene.regions, reference.regions, strict=True):
            region.material = dict(source.material)
        for boundary, source in zip(scene.boundaries, reference.boundaries, strict=True):
            boundary.condition = source.condition
        scene.source = dict(reference.source)

    empty.session.edit("physics", physics)
    assert empty.session.scene == reference


def test_adding_a_shape_selects_it_and_shows_its_form(opened, panel):
    panel.add_item("rectangle")
    assert opened.scene_dock.selected() == ("shape", "rectangle")
    assert panel.field("name").text() == "rectangle"
    assert panel.field("width").value() == 1.0 and panel.field("height").value() == 1.0
    assert [n for n, _ in opened.scene_dock.rows()["shape"]][-1] == "rectangle"


def test_names_are_made_free(opened, panel):
    panel.add_item("circle")
    panel.add_item("circle")
    names = [n for n, _ in opened.scene_dock.rows()["shape"]]
    assert names[-2:] == ["circle", "circle_2"]


def test_changing_a_shape_re_meshes_and_keeps_the_selection(opened, panel):
    opened.scene_dock.select("shape", "wall")
    panel.field("radius").setValue(3.0)
    panel.apply()
    assert opened.scene_dock.selected() == ("shape", "wall")
    nodes = opened.document.mesh.nodes
    assert nodes[:, 0].max() == pytest.approx(3.0, abs=0.02)
    assert opened.document.size == pytest.approx(6.0 / 40)


def test_renaming_a_shape_updates_the_boundary_that_names_it(opened, panel):
    opened.scene_dock.select("shape", "wall")
    panel.field("name").setText("far_wall")
    panel.apply()
    assert opened.scene_dock.selected() == ("shape", "far_wall")
    assert opened.session.scene.boundary("outer_wall").curve == Outline("far_wall")
    assert opened.document.mesh is not None


def test_a_refused_edit_changes_nothing_and_says_why(opened, panel):
    opened.scene_dock.select("shape", "wall")
    panel.field("name").setText("electrode")
    before = opened.session.scene.shapes[2].name
    panel.apply()
    assert "already exists" in panel.message()
    assert opened.session.scene.shapes[2].name == before
    assert not opened.session.history.can_undo


def test_a_refused_edit_leaves_a_half_applied_form_undone(opened, panel):
    opened.scene_dock.select("shape", "wall")
    panel.field("radius").setValue(5.0)
    panel.field("name").setText("")
    panel.apply()
    assert "empty" in panel.message()
    assert opened.session.scene.shape("wall").radius == 2.0


def test_deleting_a_shape_that_is_in_use_is_refused(opened, panel):
    opened.scene_dock.select("shape", "electrode")
    panel.field("delete").click()
    assert "used by" in panel.message() and "glass" in panel.message()
    assert len(opened.session.scene.shapes) == 3


def test_deleting_an_unused_shape(opened, panel):
    panel.add_item("circle")
    panel.field("delete").click()
    assert [n for n, _ in opened.scene_dock.rows()["shape"]] == ["electrode", "glass_outer", "wall"]
    assert opened.scene_dock.selected() == ("", "")


def test_a_region_is_built_from_shapes_and_operations(opened, panel):
    define_region(panel, "ring", [(None, "wall"), ("difference", "glass_outer")])
    region = opened.session.scene.region("ring")
    assert region.area == opened.session.scene.shape("wall") - opened.session.scene.shape(
        "glass_outer"
    )
    assert editing.area_operands(region.area) == [(None, "wall"), ("difference", "glass_outer")]


def test_a_region_form_shows_the_operands_it_was_built_from(opened, panel):
    opened.scene_dock.select("region", "air")
    assert panel.field("shape_0").currentText() == "wall"
    assert panel.field("operation_1").currentText() == "difference"
    assert panel.field("shape_1").currentText() == "glass_outer"


def test_a_boundary_can_be_a_side_of_a_rectangle(empty, panel):
    panel.add_item("rectangle")
    define_boundary(panel, "left_edge", "Side of a shape", shape="rectangle", side="left")
    assert empty.session.scene.boundary("left_edge").curve == Side("rectangle", "left")
    assert panel.field("side").currentText() == "left"


def test_a_boundary_can_be_the_interface_between_two_regions(opened, panel):
    define_boundary(panel, "interface", "Between regions", first="glass", second="air")
    assert opened.session.scene.boundary("interface").curve == Between("glass", "air")
    assert opened.document.mesh is not None


def test_a_polygon_is_edited_as_text_and_bad_text_is_explained(opened, panel):
    panel.add_item("polygon")
    panel.field("points").setPlainText("0, 0\n4, 0\n4, 3\n0, 3")
    panel.apply()
    assert opened.session.scene.shape("polygon").points == (
        (0.0, 0.0),
        (4.0, 0.0),
        (4.0, 3.0),
        (0.0, 3.0),
    )
    panel.field("points").setPlainText("0, 0\n1")
    panel.apply()
    assert "line 2" in panel.message()
    panel.field("points").setPlainText("0, 0\n1, x\n2, 2")
    panel.apply()
    assert "not two numbers" in panel.message()


def test_adding_a_region_or_boundary_needs_a_shape(empty, panel):
    panel.add_item("region")
    assert "add a shape first" in panel.message()
    panel.add_item("boundary")
    assert "add a shape first" in panel.message()
    assert empty.session.scene.regions == [] and empty.session.scene.boundaries == []


def test_undo_and_redo_through_the_edit_menu(opened, panel):
    menu = opened.menu
    assert "Undo" in menu.edit_titles()[0] and not menu._undo.isEnabled()
    panel.add_item("circle")
    assert menu._undo.isEnabled() and menu.edit_titles()[0] == "Undo add circle"
    menu._undo.trigger()
    assert "circle" not in [n for n, _ in opened.scene_dock.rows()["shape"]]
    assert menu._redo.isEnabled() and menu.edit_titles()[1] == "Redo add circle"
    menu._redo.trigger()
    assert "circle" in [n for n, _ in opened.scene_dock.rows()["shape"]]


def test_undo_restores_the_mesh_preview_too(opened, panel):
    opened.scene_dock.select("shape", "wall")
    panel.field("radius").setValue(4.0)
    panel.apply()
    assert opened.document.mesh.nodes[:, 0].max() == pytest.approx(4.0, abs=0.03)
    opened.session.undo()
    assert opened.document.mesh.nodes[:, 0].max() == pytest.approx(2.0, abs=0.02)
    assert opened.session.scene.shape("wall").radius == 2.0


def test_an_edit_is_one_undo_step_even_with_rename_and_parameters(opened, panel):
    opened.scene_dock.select("shape", "glass_outer")
    panel.field("name").setText("shell_outer")
    panel.field("radius").setValue(0.6)
    panel.apply()
    opened.session.undo()
    shape = opened.session.scene.shapes[1]
    assert (shape.name, shape.radius) == ("glass_outer", 0.5)
    assert not opened.session.history.can_undo


def test_the_title_shows_unsaved_changes_and_save_clears_them(opened, panel, tmp_path):
    assert not opened.windowTitle().endswith("*")
    panel.add_item("circle")
    assert opened.windowTitle().endswith("capacitor.scene.json*")
    target = tmp_path / "edited.scene.json"
    assert opened.save(target)
    assert opened.windowTitle().endswith("edited.scene.json")
    assert not opened.session.dirty


def test_a_saved_scene_reopens_equal(empty, panel, tmp_path, window):
    add_circle(panel, "disk", 1.5, (1.0, -1.0))
    define_region(panel, "plate", [(None, "disk")])
    define_boundary(panel, "rim", "Outline of a shape", shape="disk")
    target = tmp_path / "plate.scene.json"
    assert window.save(target)
    saved = window.session.scene
    assert window.open_path(target)
    assert window.session.scene == saved
    assert window.session.scene.shape("disk") == Circle("disk", (1.0, -1.0), 1.5)


def test_a_new_scene_is_untitled(empty):
    assert empty.windowTitle() == "FEM Studio - untitled.scene.json"
    assert all(rows == [] for rows in empty.scene_dock.rows().values())
    assert not empty.session.history.can_undo


def test_a_mesh_only_document_cannot_be_edited(window, panel):
    assert window.open_path(DATA / "two_materials.geo")
    assert not panel.can_add()
    assert ("editing", "open a scene to edit") in panel.rows()
    assert not window.menu._save.isEnabled()


def test_the_default_boundary_row_cannot_be_edited_as_a_boundary(window, panel, tmp_path):
    from femstudio.core.scene.boundary import DEFAULT_BOUNDARY_NAME, BoundaryCondition
    from femstudio.core.scene.serialization import save_scene

    scene = capacitor_scene()
    scene.boundaries.pop()
    scene.default_boundary = BoundaryCondition("dirichlet", {"g": "0"})
    path = tmp_path / "scene.json"
    save_scene(scene, path)
    assert window.open_path(path)
    window.scene_dock.select("boundary", DEFAULT_BOUNDARY_NAME)
    assert ("curve", "outer edges no boundary names") in panel.rows()


def test_edits_keep_the_camera_and_the_highlight(opened, panel):
    view = opened.viewport.geometry_view
    opened.scene_dock.select("region", "glass")
    assert view.highlighted() == ("region", "glass")
    opened.scene_dock.select("shape", "electrode")
    panel.field("radius").setValue(0.25)
    panel.apply()
    assert view.highlighted() == ("shape", "electrode")


def test_nodes_of_an_edited_scene_stay_inside_the_new_geometry(opened, panel):
    opened.scene_dock.select("shape", "wall")
    panel.field("radius").setValue(1.0)
    panel.apply()
    radii = np.linalg.norm(opened.document.mesh.nodes, axis=1)
    assert radii.max() == pytest.approx(1.0, abs=0.01)


def test_rectangle_form_edits_corner_and_size(empty, panel):
    panel.add_item("rectangle")
    panel.field("corner_x").setValue(-1.0)
    panel.field("width").setValue(3.0)
    panel.apply()
    assert empty.session.scene.shape("rectangle") == Rectangle("rectangle", (-1.0, 0.0), 3.0, 1.0)


def test_polygon_default_is_a_triangle(empty, panel):
    panel.add_item("polygon")
    assert empty.session.scene.shape("polygon") == Polygon(
        "polygon", ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))
    )


def _settle(window):
    from PySide6.QtWidgets import QApplication

    for _ in range(4):
        QApplication.processEvents()


def _top(widget, panel) -> int:
    from PySide6.QtCore import QPoint

    return widget.mapTo(panel, QPoint(0, 0)).y()


def test_operand_rows_appear_in_the_order_they_were_given(opened, panel):
    opened.scene_dock.select("region", "air")
    _settle(opened)
    assert _top(panel.field("shape_0"), panel) < _top(panel.field("shape_1"), panel)
    panel.field("add_operand").click()
    _settle(opened)
    assert _top(panel.field("shape_1"), panel) < _top(panel.field("shape_2"), panel)
    assert panel.field("operation_2").currentText() == "union"


def _headings(panel) -> list[str]:
    from PySide6.QtWidgets import QLabel

    return [
        w.text()
        for w in panel.findChildren(QLabel)
        if w.property("role") == "heading" and w.isVisible()
    ]


def test_only_the_current_selections_section_is_shown(opened, panel):
    opened.scene_dock.select("region", "glass")
    _settle(opened)
    assert _headings(panel) == ["Add", "Region: glass"]
    opened.scene_dock.select("shape", "wall")
    _settle(opened)
    assert _headings(panel) == ["Add", "Shape: wall"]
    opened.scene_dock.clear_selection()
    _settle(opened)
    assert _headings(panel) == ["Add", "Scene"]


@pytest.mark.parametrize(
    ("kind", "name"),
    [("shape", "wall"), ("region", "glass"), ("boundary", "inner_electrode")],
)
def test_forms_fit_inside_the_properties_dock(opened, panel, kind, name):
    opened.scene_dock.select(kind, name)
    _settle(opened)
    width = panel.width()
    assert width > 0
    for widget in panel.findChildren(object):
        if hasattr(widget, "isVisible") and widget.isVisible() and hasattr(widget, "mapTo"):
            right = widget.mapTo(panel, widget.rect().topRight()).x()
            assert right <= width + 1, f"{widget.objectName() or type(widget).__name__} clips"
