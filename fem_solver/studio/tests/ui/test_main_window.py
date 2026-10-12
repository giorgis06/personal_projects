import pytest
from femstudio.ui.main_window import MainWindow
from femstudio.ui.theme import tokens as t
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget
from tests.ui.conftest import DATA, EXAMPLE

pytestmark = pytest.mark.ui


@pytest.fixture
def window(qtbot):
    window = MainWindow()
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
    assert opened.properties.panel("Geometry").rows() == [("area", "(glass_outer - electrode)")]
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
