import numpy as np
import pytest
from femstudio.ui.theme import tokens as t

pytestmark = pytest.mark.ui


@pytest.fixture(autouse=True)
def _off_screen_plotters(monkeypatch):
    """Draw with off-screen plotters on every platform.

    Two real GL widgets per window, over many windows, made on-screen runs of the whole suite
    fail often (see the plan's known debt). The drawing code is the same; only the widget that
    hosts the plotter differs, and that is checked by hand on screen.
    """
    from femstudio.ui.views import plotter_view

    monkeypatch.setattr(
        plotter_view, "HEADLESS_PLATFORMS", plotter_view.HEADLESS_PLATFORMS + ("xcb", "wayland")
    )


def fields(window):
    return window.results.results


@pytest.fixture
def viewed(solved):
    """The solved window with both field views made: a view is drawn when first shown."""
    solved.viewport.show_tab("3D surface")
    solved.viewport.show_tab("Heatmap")
    return solved


def test_a_finished_run_is_shown_in_both_views_and_the_results_step(solved):
    assert solved.workflow.step() == "Results"
    assert solved.viewport.current_title() == "Heatmap"
    assert solved.viewport.surface_view.shown() is None  # not made until its tab is first shown
    solved.viewport.show_tab("3D surface")
    assert solved.scene_dock.selected() == ("run", "run 1")
    assert solved.viewport.heatmap_view.shown() == (1, "u", t.DEFAULT_COLOUR_MAP)
    assert solved.viewport.surface_view.shown() == solved.viewport.heatmap_view.shown()
    assert "[results] run 1 loaded" in solved.log.lines()


def test_both_views_draw_the_same_numbers_as_the_field(viewed):
    expected = fields(viewed).scalars("u")
    np.testing.assert_array_equal(viewed.viewport.heatmap_view.drawn_values(), expected)
    np.testing.assert_array_equal(viewed.viewport.surface_view.drawn_values(), expected)
    assert viewed.viewport.heatmap_view.drawn_range() == pytest.approx(
        viewed.results.colour_range()
    )
    assert viewed.viewport.surface_view.drawn_range() == viewed.viewport.heatmap_view.drawn_range()


def test_the_colour_bar_names_the_field_and_its_unit(viewed):
    for view in (viewed.viewport.heatmap_view, viewed.viewport.surface_view):
        assert view.bar_count() == 1
        assert view.bar_title() == "Potential [V]"


def test_the_field_selector_offers_the_derived_fields(viewed):
    panel = viewed.properties.panel("Results")
    combo = panel.widget("field")
    names = [combo.itemData(i) for i in range(combo.count())]
    assert names == ["u", "E", "E_magnitude", "energy_density"]
    assert combo.itemText(2) == "Field magnitude [V/m]"


def test_choosing_a_derived_field_redraws_both_views_with_its_values(viewed):
    viewed.results.set_field("energy_density")
    expected = fields(viewed).scalars("energy_density")
    assert len(expected) == fields(viewed).mesh.n_triangles
    np.testing.assert_array_equal(viewed.viewport.heatmap_view.drawn_values(), expected)
    # the surface needs a height at every node, so a per-triangle field is averaged there
    assert len(viewed.viewport.surface_view.drawn_values()) == fields(viewed).mesh.n_nodes
    assert viewed.viewport.heatmap_view.bar_title() == "Energy density [J/m^3]"
    assert viewed.viewport.heatmap_view.bar_count() == 1


def test_a_vector_field_is_drawn_by_its_magnitude(viewed):
    viewed.results.set_field("E")
    np.testing.assert_allclose(
        viewed.viewport.heatmap_view.drawn_values(), fields(viewed).scalars("E_magnitude")
    )


def test_the_panel_follows_the_choices_made_in_it(viewed):
    panel = viewed.properties.panel("Results")
    combo = panel.widget("field")
    combo.setCurrentIndex(combo.findData("E_magnitude"))
    combo.activated.emit(combo.currentIndex())
    assert viewed.results.display.field == "E_magnitude"
    assert viewed.viewport.heatmap_view.shown()[1] == "E_magnitude"
    assert viewed.viewport.surface_view.shown()[1] == "E_magnitude"


def test_a_colour_map_applies_to_both_views(viewed):
    panel = viewed.properties.panel("Results")
    colours = panel.widget("colours")
    assert [colours.itemData(i) for i in range(colours.count())] == list(t.COLOUR_MAPS)
    colours.setCurrentIndex(colours.findData("inferno"))
    colours.activated.emit(colours.currentIndex())
    assert viewed.viewport.heatmap_view.shown()[2] == "inferno"
    assert viewed.viewport.surface_view.shown()[2] == "inferno"


def test_the_mesh_overlay_is_off_until_asked_for(viewed):
    panel = viewed.properties.panel("Results")
    assert not viewed.viewport.heatmap_view.show_edges()
    panel.widget("overlay").setChecked(True)
    assert viewed.viewport.heatmap_view.show_edges()
    assert viewed.viewport.surface_view.show_edges()
    panel.widget("overlay").setChecked(False)
    assert not viewed.viewport.heatmap_view.show_edges()


def test_a_range_typed_in_the_panel_sets_the_colours_of_both_views(viewed):
    panel = viewed.properties.panel("Results")
    panel.widget("auto_range").setChecked(False)
    panel.widget("low").set_value(-1.0)
    panel.widget("high").set_value(2.0)
    panel.widget("apply_range").click()
    assert viewed.results.colour_range() == (-1.0, 2.0)
    assert viewed.viewport.heatmap_view.drawn_range() == (-1.0, 2.0)
    assert viewed.viewport.surface_view.drawn_range() == (-1.0, 2.0)
    panel.widget("auto_range").setChecked(True)
    assert viewed.results.display.auto_range
    assert viewed.viewport.heatmap_view.drawn_range() == pytest.approx(
        fields(viewed).value_range("u")
    )


def test_a_reversed_or_unreadable_range_is_refused_and_the_old_one_stays(viewed):
    panel = viewed.properties.panel("Results")
    before = viewed.results.colour_range()
    panel.widget("auto_range").setChecked(False)
    panel.widget("low").set_value(5.0)
    panel.widget("high").set_value(1.0)
    panel.widget("apply_range").click()
    assert "smaller to a larger" in panel.widget("range_message").text()
    assert viewed.viewport.heatmap_view.drawn_range() == pytest.approx(before)
    panel.widget("high").setText("")
    panel.widget("apply_range").click()
    assert "not a number" in panel.widget("range_message").text()


def test_the_probe_reads_the_field_array_at_a_node(viewed):
    results = fields(viewed)
    node = results.mesh.n_nodes // 3
    x, y = results.mesh.nodes[node]
    viewed.results.set_probe(float(x), float(y))
    reading = viewed.results.reading()
    assert reading.value == pytest.approx(results.scalars("u")[node], rel=1e-9, abs=1e-12)
    panel = viewed.properties.panel("Results")
    rows = dict(panel.probe_rows())
    assert rows["u"] == f"{reading.value:.5g} V"
    assert panel.widget("probe_x").value() == pytest.approx(x)


def test_the_probe_of_a_triangle_field_is_the_triangles_value(viewed):
    results = fields(viewed)
    viewed.results.set_field("energy_density")
    triangle = results.mesh.n_triangles // 2
    x, y = results.mesh.nodes[results.mesh.triangles[triangle]].mean(axis=0)
    viewed.results.set_probe(float(x), float(y))
    reading = viewed.results.reading()
    assert reading.triangle == triangle
    assert reading.value == results.scalars("energy_density")[triangle]


def test_a_vector_probe_shows_its_components(viewed):
    results = fields(viewed)
    viewed.results.set_field("E")
    x, y = results.mesh.nodes[results.mesh.triangles[0]].mean(axis=0)
    viewed.results.set_probe(float(x), float(y))
    rows = dict(viewed.properties.panel("Results").probe_rows())
    assert "components" in rows


def test_a_probe_outside_the_mesh_says_so(viewed):
    panel = viewed.properties.panel("Results")
    panel.widget("probe_x").set_value(1e6)
    panel.widget("probe_y").set_value(1e6)
    panel.widget("place_probe").click()
    assert viewed.results.reading() is None
    assert panel.probe_rows() == [("", "Outside the mesh.")]


def test_the_probe_is_marked_in_both_views_at_the_position_it_reads(viewed):
    results = fields(viewed)
    x, y = results.mesh.nodes[0]
    viewed.results.set_probe(float(x), float(y))
    flat = viewed.viewport.heatmap_view.probe_position()
    raised = viewed.viewport.surface_view.probe_position()
    assert flat[:2] == pytest.approx((x, y))
    assert raised[:2] == pytest.approx((x, y))
    assert raised[2] != flat[2] or results.value_range("u")[0] == results.value_range("u")[1]
    viewed.results.clear_probe()
    assert viewed.viewport.heatmap_view.probe_position() is None


def display_position(view, x, y):
    renderer = view._plotter.renderer
    renderer.SetWorldPoint(x, y, 0.0, 1.0)
    renderer.WorldToDisplay()
    return renderer.GetDisplayPoint()[:2]


def test_a_click_in_the_view_places_the_probe_where_the_field_is_under_it(viewed):
    view = viewed.viewport.heatmap_view
    results = fields(viewed)
    x, y = results.mesh.nodes[results.mesh.triangles[10]].mean(axis=0)
    assert view.pick(*display_position(view, x, y))
    px, py = viewed.results.probe
    assert (px, py) == pytest.approx((x, y), abs=1e-3)
    assert viewed.results.reading().triangle == 10


def test_a_click_off_the_field_places_nothing(viewed):
    view = viewed.viewport.heatmap_view
    assert not view.pick(0, 0)
    assert viewed.results.probe is None


def test_selecting_a_run_without_a_result_says_why(viewed):
    run = viewed.session.runs()[0]
    (run.folder / "status.json").write_text('{"state": "failed", "message": "diverged"}')
    viewed.results.clear()
    viewed._load_run("run 1")
    panel = viewed.properties.panel("Results")
    assert viewed.results.results is None
    assert panel.text() == "run 1 has no result: it failed"
    assert viewed.viewport.heatmap_view.shown() is None
    assert "has no result" in viewed.viewport.heatmap_view.note()


def test_selecting_the_run_again_shows_its_result(viewed):
    viewed.results.clear()
    assert viewed.viewport.heatmap_view.shown() is None
    viewed.scene_dock.select("region", "glass")
    viewed.scene_dock.select("run", "run 1")
    assert viewed.viewport.heatmap_view.shown() == (1, "u", t.DEFAULT_COLOUR_MAP)


def test_selecting_a_region_keeps_the_result_on_show(viewed):
    viewed.scene_dock.select("region", "glass")
    assert viewed.viewport.heatmap_view.shown() is not None


def test_a_new_scene_clears_the_result(qtbot, viewed):
    assert viewed.new_scene()
    assert viewed.results.results is None
    assert viewed.viewport.heatmap_view.shown() is None
    assert viewed.viewport.surface_view.shown() is None


def test_nothing_is_shown_before_any_run(opened):
    assert opened.viewport.heatmap_view.shown() is None
    assert opened.viewport.surface_view.note().startswith("No result yet")
    assert opened.properties.panel("Results").text() == "No result yet."


def test_the_field_keeps_its_choice_when_another_run_replaces_it(qtbot, viewed):
    viewed.results.set_field("E_magnitude")
    viewed.results.set_colour_map("coolwarm")
    with qtbot.waitSignal(viewed.runner.finished, timeout=30000):
        viewed.workflow._run.click()
    assert viewed.viewport.heatmap_view.shown() == (2, "E_magnitude", "coolwarm")


def test_a_run_not_yet_solved_is_described_in_words(viewed):
    run = viewed.session.runs()[0]
    for state, words in (("created", "it has not been solved"), ("running", "it is still running")):
        (run.folder / "status.json").write_text(f'{{"state": "{state}"}}')
        viewed._load_run("run 1")
        assert viewed.results.message == f"run 1 has no result: {words}"


def test_narrowing_the_range_keeps_the_surface_inside_its_extent(viewed):
    viewed.results.set_range(0.0, 1e-3)
    points = viewed.viewport.surface_view._poly.points
    side = float(np.ptp(fields(viewed).mesh.nodes, axis=0).max())
    assert points[:, 2].min() >= 0.0
    assert points[:, 2].max() <= t.SURFACE_HEIGHT * side * (1 + 1e-9)
