import pytest
from femstudio.ui.main_window import MainWindow
from femstudio.ui.theme import tokens as t
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget
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
def opened(window):
    assert window.open_path(EXAMPLE)
    return window


def test_window_opens(window):
    assert window.isVisible()
    assert window.windowTitle() == "FEM Studio"


def test_arrangement_matches_the_workbench_design(window):
    assert window.menu.menu_titles() == ["File", "Edit", "View", "Run", "Help"]
    assert window.workflow.steps() == ["Geometry", "Physics", "Mesh", "Solve", "Results"]
    assert window.viewport.tab_titles() == ["Heatmap", "3D surface", "Mesh", "Geometry"]
    assert window.dockWidgetArea(window.scene_dock) == Qt.DockWidgetArea.LeftDockWidgetArea
    assert window.dockWidgetArea(window.properties) == Qt.DockWidgetArea.RightDockWidgetArea
    assert window.dockWidgetArea(window.log) == Qt.DockWidgetArea.BottomDockWidgetArea
    assert window.centralWidget() is window.viewport
    assert window.statusBar() is window.status
    assert window.workflow.backends() == ["fem", "mock"]
    assert not window.workflow.run_enabled()


def test_regions_are_stacked_top_to_bottom(window):
    top = lambda widget: widget.mapTo(window, widget.rect().topLeft()).y()  # noqa: E731
    assert top(window.menu) < top(window.workflow) < top(window.viewport) < top(window.log)
    assert top(window.log) < top(window.status)
    assert window.scene_dock.x() < window.viewport.x() < window.properties.x()


def test_the_capacitor_opens_with_its_names(opened):
    rows = opened.scene_dock.rows()
    assert [name for name, _ in rows["shape"]] == ["electrode", "glass_outer", "wall"]
    assert [name for name, _ in rows["region"]] == ["glass", "air"]
    assert [name for name, _ in rows["boundary"]] == ["inner_electrode", "outer_wall"]
    assert "capacitor.scene.json" in opened.windowTitle()
    mesh = opened.document.mesh
    assert opened.status.texts()[1].replace(" ", "") == f"{mesh.n_nodes:,}nodes".replace(",", "")
    assert any(line.startswith("[open]") for line in opened.log.lines())


def test_the_mesher_log_reaches_the_log_dock(opened):
    assert any("Done reading" in line or "nodes" in line for line in opened.log.lines())


def test_selecting_a_scene_row_highlights_that_part_in_the_viewport(opened):
    opened.scene_dock.select("region", "glass")
    for view in (opened.viewport.geometry_view, opened.viewport.mesh_view):
        assert view.highlighted() == ("region", "glass")
        assert view.style("region", "glass").opacity == 1.0
        assert view.style("region", "air").opacity == t.OPACITY_DIMMED
    opened.scene_dock.select("boundary", "inner_electrode")
    assert opened.viewport.geometry_view.highlighted() == ("boundary", "inner_electrode")
    assert opened.viewport.geometry_view.style("boundary", "inner_electrode").width == (
        t.LINE_WIDTH_SELECTED
    )
    opened.scene_dock.select("shape", "wall")
    assert opened.viewport.geometry_view.style("shape", "wall").colour == t.ACCENT


def test_selecting_a_row_shows_its_fields_in_the_properties_dock(opened):
    opened.scene_dock.select("region", "glass")
    geometry = opened.properties.panel("Geometry")
    assert geometry.field("name").text() == "glass"
    assert geometry.field("shape_0").currentText() == "glass_outer"
    assert geometry.field("operation_1").currentText() == "difference"
    assert geometry.field("shape_1").currentText() == "electrode"
    assert opened.properties.panel("Physics").rows() == [("epsilon", "4")]
    opened.scene_dock.select("boundary", "inner_electrode")
    assert opened.properties.panel("Physics").rows() == [("kind", "Fixed potential"), ("g", "5 V")]


def test_choosing_a_step_selects_its_panel_and_viewport_tab(opened):
    expected = {
        "Geometry": ("Geometry", "Geometry"),
        "Physics": ("Physics", "Geometry"),
        "Mesh": ("Mesh", "Mesh"),
        "Solve": ("Solve", "Mesh"),
        "Results": ("Results", "Heatmap"),
    }
    for step, (panel, tab) in expected.items():
        opened.workflow._buttons[step].click()
        assert opened.properties.current_step() == panel
        assert opened.viewport.current_title() == tab
        assert opened.scene_dock.isVisible()


def test_going_back_to_an_earlier_step_still_works(opened):
    opened.workflow._buttons["Results"].click()
    opened.workflow._buttons["Geometry"].click()
    assert opened.viewport.current_title() == "Geometry"
    assert opened.properties.current_step() == "Geometry"


def test_selection_survives_a_change_of_step(opened):
    opened.scene_dock.select("region", "air")
    opened.workflow._buttons["Mesh"].click()
    assert opened.viewport.mesh_view.highlighted() == ("region", "air")


def test_docks_keep_their_width_when_the_window_grows(window):
    window.resize(1180, 700)
    window.repaint()
    before = (window.scene_dock.width(), window.properties.width(), window.viewport.width())
    window.resize(1500, 700)
    window.repaint()
    after = (window.scene_dock.width(), window.properties.width(), window.viewport.width())
    assert after[0] == before[0] and after[1] == before[1]
    assert after[2] - before[2] == pytest.approx(320, abs=2)


def test_docks_are_movable_and_closable(window):
    wanted = QDockWidget.DockWidgetFeature.DockWidgetMovable
    wanted |= QDockWidget.DockWidgetFeature.DockWidgetClosable
    for dock in (window.scene_dock, window.properties, window.log):
        assert dock.features() & wanted == wanted


def test_a_closed_dock_comes_back_from_the_view_menu(window):
    window.log.close()
    assert not window.log.isVisible()
    window.log.toggleViewAction().trigger()
    assert window.log.isVisible()


def test_reset_layout_restores_the_default_arrangement(window):
    window.log.close()
    window.scene_dock.setFloating(True)
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, window.properties)
    window.removeDockWidget(window.properties)
    window.menu.resetLayoutRequested.emit()
    assert window.log.isVisible() and window.properties.isVisible()
    assert not window.scene_dock.isFloating()
    assert window.dockWidgetArea(window.scene_dock) == Qt.DockWidgetArea.LeftDockWidgetArea
    assert window.dockWidgetArea(window.properties) == Qt.DockWidgetArea.RightDockWidgetArea
    assert window.dockWidgetArea(window.log) == Qt.DockWidgetArea.BottomDockWidgetArea


def test_a_geo_file_opens_as_a_mesh(window):
    assert window.open_path(DATA / "two_materials.geo")
    rows = window.scene_dock.rows()
    assert {name for name, _ in rows["region"]} == {"glass", "air"}
    assert rows["shape"] == []
    window.scene_dock.select("region", "glass")
    assert window.viewport.geometry_view.highlighted() == ("region", "glass")


def test_a_project_folder_opens_with_its_runs(window, tmp_path):
    from examples.capacitor import capacitor_scene
    from femstudio.core.project.project import Project

    project = Project.create(tmp_path / "proj", capacitor_scene())
    project.new_run()
    assert window.open_path(tmp_path / "proj")
    assert window.scene_dock.rows()["run"] == [("run 1", "created")]


def test_a_file_that_cannot_be_opened_is_reported_not_raised(window, errors, tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("x")
    assert window.open_path(path) is False
    assert errors and errors[0][0] == "Cannot open notes.txt"
    assert any(line.startswith("[error]") for line in window.log.lines())
    assert window.document is None


def test_a_failed_open_keeps_the_previous_document(opened, errors, tmp_path):
    path = tmp_path / "scene.json"
    path.write_text("{ not json")
    assert opened.open_path(path) is False
    assert opened.document is not None
    assert [n for n, _ in opened.scene_dock.rows()["region"]] == ["glass", "air"]


def test_validation_summary_updates_for_the_open_scene(opened):
    assert opened.status.texts()[0] == "Validation: 0 errors, 0 warnings"
    assert opened.status.findings() == []


def unmeshable(tmp_path, change):
    from examples.capacitor import capacitor_scene
    from femstudio.core.scene.serialization import save_scene

    scene = capacitor_scene()
    change(scene)
    path = tmp_path / "scene.json"
    save_scene(scene, path)
    return path


def test_a_scene_with_unnamed_outer_edges_opens_to_be_fixed(window, tmp_path):
    path = unmeshable(tmp_path, lambda scene: scene.boundaries.pop())
    assert window.open_path(path)
    assert [n for n, _ in window.scene_dock.rows()["region"]] == ["glass", "air"]
    assert window.status.texts()[0] == "Validation: 1 error, 0 warnings"
    assert "named by no boundary" in window.status.findings()[0].message
    assert window.viewport.geometry_view.note().startswith("Not meshed:")
    assert any(line.startswith("[mesh] not built") for line in window.log.lines())
    window.workflow._buttons["Mesh"].click()
    assert dict(window.properties.panel("Mesh").rows())["mesh"] == "not built"


def test_shape_outlines_are_drawn_without_a_mesh(window, tmp_path):
    path = unmeshable(tmp_path, lambda scene: scene.regions[0].material.clear())
    assert window.open_path(path)
    view = window.viewport.geometry_view
    assert view.actor_style("shape", "wall") is not None
    assert view.actor_style("region", "glass") is None
    window.scene_dock.select("shape", "wall")
    assert view.actor_style("shape", "wall").colour == t.ACCENT


def test_an_empty_scene_opens_empty(window, tmp_path):
    path = unmeshable(
        tmp_path,
        lambda scene: (scene.shapes.clear(), scene.regions.clear(), scene.boundaries.clear()),
    )
    assert window.open_path(path)
    assert all(rows == [] for rows in window.scene_dock.rows().values())
    assert "no shapes" in window.viewport.geometry_view.note()


def test_the_default_boundary_is_a_row_and_is_drawn(window, tmp_path):
    from femstudio.core.scene.boundary import DEFAULT_BOUNDARY_NAME, BoundaryCondition

    def change(scene):
        scene.boundaries.pop()
        scene.default_boundary = BoundaryCondition("dirichlet", {"g": "0"})

    assert window.open_path(unmeshable(tmp_path, change))
    boundaries = window.scene_dock.rows()["boundary"]
    assert boundaries == [("inner_electrode", "5 V"), (DEFAULT_BOUNDARY_NAME, "0 V")]
    view = window.viewport.geometry_view
    assert view.actor_style("boundary", DEFAULT_BOUNDARY_NAME) is not None
    window.scene_dock.select("boundary", DEFAULT_BOUNDARY_NAME)
    assert view.style("boundary", DEFAULT_BOUNDARY_NAME).width == t.LINE_WIDTH_SELECTED
    assert window.properties.panel("Geometry").rows() == [
        ("curve", "outer edges no boundary names")
    ]
    assert window.properties.panel("Physics").rows() == [("kind", "Fixed potential"), ("g", "0 V")]


def test_a_mesh_that_names_nothing_is_drawn_and_explained(window, tmp_path):
    path = tmp_path / "plain.geo"
    path.write_text(
        'SetFactory("OpenCASCADE");\nRectangle(1) = {0, 0, 0, 1, 1};\nMesh.MeshSizeMax = 0.5;\n'
    )
    assert window.open_path(path)
    assert window.viewport.geometry_view.actor_style("unnamed", "") is not None
    assert ("note", "this mesh names no regions or boundaries") in (
        window.properties.panel("Geometry").rows()
    )


def test_scene_rows_are_indented_under_their_group(window):
    assert window.open_path(EXAMPLE)
    tree = window.scene_dock._tree
    group = tree.topLevelItem(0)
    row = group.child(0)
    assert tree.visualItemRect(row).x() - tree.visualItemRect(group).x() == t.TREE_INDENT
    assert tree.indentation() == t.TREE_INDENT


def test_a_step_set_from_code_moves_the_panel_and_the_tab(window):
    window.workflow.set_step("Results")
    assert window.properties.current_step() == "Results"
    assert window.viewport.current_title() == "Heatmap"


def row_height(window) -> int:
    tree = window.scene_dock._tree
    group = tree.topLevelItem(0)
    return tree.visualItemRect(group.child(0)).height()


def test_zoom_in_scales_text_rows_and_paddings_by_the_factor(window):
    assert window.open_path(EXAMPLE)
    base_font = window.font().pointSizeF()
    base_row = row_height(window)
    base_pad = window.properties._body_layout.contentsMargins().left()
    assert base_font == t.BASE_PT and base_row == t.ROW_HEIGHT

    window.set_zoom(1.5)
    assert window.font().pointSizeF() == pytest.approx(base_font * 1.5)
    assert row_height(window) == pytest.approx(base_row * 1.5, abs=1)
    assert window.properties._body_layout.contentsMargins().left() == round(base_pad * 1.5)
    assert window.status.zoom_text() == "Zoom 150 %"
    assert f"{t.BASE_PT * 1.5:g}pt" in window.styleSheet()


def test_zoom_also_scales_dock_widths_swatches_and_value_fonts(window):
    assert window.open_path(EXAMPLE)
    window.show()
    tree = window.scene_dock._tree
    swatch_before = tree.iconSize().width()
    indent_before = tree.indentation()
    window.set_zoom(2.0)
    assert tree.iconSize().width() == 2 * swatch_before
    assert tree.indentation() == 2 * indent_before
    item = tree.topLevelItem(1).child(0)
    assert item.font(1).pointSizeF() == pytest.approx(2.0 * t.BASE_PT)
    assert window.scene_dock.swatches("region") == [t.region_colour(0), t.region_colour(1)]


def test_reset_restores_the_token_values(window):
    assert window.open_path(EXAMPLE)
    window.set_zoom(1.8)
    window.menu.zoomResetRequested.emit()
    assert window.font().pointSizeF() == t.BASE_PT
    assert row_height(window) == t.ROW_HEIGHT
    assert window.status.zoom_text() == "Zoom 100 %"
    assert window.properties._body_layout.contentsMargins().left() == t.PANEL_PAD


def test_the_limits_hold(window):
    for _ in range(30):
        window.menu.zoomInRequested.emit()
    assert window.status.zoom_text() == "Zoom 200 %"
    assert not window.menu._zoom_in.isEnabled() and window.menu._zoom_out.isEnabled()
    for _ in range(40):
        window.menu.zoomOutRequested.emit()
    assert window.status.zoom_text() == "Zoom 70 %"
    assert window.menu._zoom_in.isEnabled() and not window.menu._zoom_out.isEnabled()


def test_zoom_steps_by_ten_percent(window):
    window.menu.zoomInRequested.emit()
    assert window.status.zoom_text() == "Zoom 110 %"
    window.menu.zoomOutRequested.emit()
    window.menu.zoomOutRequested.emit()
    assert window.status.zoom_text() == "Zoom 90 %"


def test_zoom_shortcuts(window):
    assert window.menu.zoom_shortcuts() == {
        "in": ["Ctrl++", "Ctrl+="],
        "out": ["Ctrl+-"],
        "reset": ["Ctrl+0"],
    }


def test_the_choice_is_remembered_between_sessions(qtbot, settings):
    first = MainWindow(settings)
    qtbot.addWidget(first)
    first.set_zoom(1.4)
    second = MainWindow(settings)
    qtbot.addWidget(second)
    assert second.status.zoom_text() == "Zoom 140 %"
    assert second.font().pointSizeF() == pytest.approx(t.BASE_PT * 1.4)


def test_zoom_leaves_the_selection_and_the_highlight_alone(opened):
    opened.scene_dock.select("region", "glass")
    opened.set_zoom(1.3)
    assert opened.viewport.geometry_view.highlighted() == ("region", "glass")
    assert opened.properties.panel("Physics").rows() == [("epsilon", "4")]


def test_zoomed_widgets_created_later_are_sized_at_the_current_zoom(window, qtbot):
    window.set_zoom(1.5)
    assert window.open_path(EXAMPLE)
    window.scene_dock.select("region", "glass")
    grid = window.properties.panel("Mesh")._grid
    assert grid._layout.verticalSpacing() == round(t.GAP * 1.5)


def test_a_stored_nan_does_not_stop_the_window_opening(qtbot, settings):
    settings.setValue("interface/zoom", "nan")
    window = MainWindow(settings)
    qtbot.addWidget(window)
    assert window.status.zoom_text() == "Zoom 100 %"
