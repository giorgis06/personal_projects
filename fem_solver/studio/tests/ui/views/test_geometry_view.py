from pathlib import Path

import numpy as np
import pytest
from examples.capacitor import capacitor_scene
from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.project.document import Document, open_document
from femstudio.ui.theme import tokens as t
from femstudio.ui.views.geometry_view import (
    GeometryView,
    element_styles,
    lines_of,
    polyline_of,
    surface_of,
)
from femstudio.ui.views.mesh_view import MeshView

EXAMPLE = Path(__file__).resolve().parents[3] / "examples" / "capacitor.scene.json"


@pytest.fixture
def mesh():
    nodes = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [0.5, 0.5]], dtype=float)
    return MeshData(
        nodes=nodes,
        node_tags=np.arange(1, 6),
        triangles=np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]]),
        edges=np.array([[0, 1], [1, 2], [2, 3], [3, 0]]),
        regions={"low": np.array([0, 1]), "high": np.array([2, 3])},
        boundaries={"bottom": np.array([0]), "all": np.array([0, 1, 2, 3])},
    )


def total_length(lines) -> float:
    return float(lines.compute_cell_sizes(length=True, area=False, volume=False)["Length"].sum())


def test_surface_holds_the_triangles_asked_for(mesh):
    surface = surface_of(mesh, mesh.regions["low"])
    assert surface.n_cells == 2
    assert surface.bounds == pytest.approx((0.0, 1.0, 0.0, 1.0, 0.0, 0.0))
    assert surface.area == pytest.approx(0.5)


def test_lines_hold_the_edges_asked_for(mesh):
    lines = lines_of(mesh, mesh.boundaries["all"])
    assert lines.n_cells == 4
    assert total_length(lines) == pytest.approx(4.0)


def test_polyline_through_points():
    line = polyline_of([(0.0, 0.0), (3.0, 0.0), (3.0, 4.0)])
    assert total_length(line) == pytest.approx(7.0)


def styles(selected=("", "")):
    return element_styles(["s1", "s2"], ["glass", "air"], ["inner", "outer"], selected)


def test_nothing_selected_gives_every_element_its_own_colour():
    result = styles()
    assert result[("region", "glass")].colour == t.region_colour(0)
    assert result[("region", "air")].colour == t.region_colour(1)
    assert result[("boundary", "outer")].colour == t.boundary_colour(1)
    assert {s.opacity for k, s in result.items() if k[0] == "region"} == {t.OPACITY}


def test_selected_region_is_full_and_the_others_recede():
    result = styles(("region", "glass"))
    assert result[("region", "glass")].opacity == 1.0
    assert result[("region", "air")].opacity == t.OPACITY_DIMMED


def test_selected_boundary_is_thick_and_the_others_recede():
    result = styles(("boundary", "inner"))
    assert result[("boundary", "inner")].width == t.LINE_WIDTH_SELECTED
    assert result[("boundary", "inner")].opacity == 1.0
    assert result[("boundary", "outer")].width == t.LINE_WIDTH
    assert result[("boundary", "outer")].opacity == t.OPACITY_DIMMED


def test_selected_shape_outline_takes_the_accent_colour():
    result = styles(("shape", "s2"))
    assert result[("shape", "s2")].colour == t.ACCENT
    assert result[("shape", "s1")].colour == t.SHAPE_OUTLINE


@pytest.mark.ui
def test_view_draws_each_named_part_and_highlights_one(qtbot, mesh):
    view = GeometryView()
    qtbot.addWidget(view)
    view.set_document(Document(source=None, mesh=mesh))
    assert view.can_draw
    assert view.actor_style("region", "low").colour == t.region_colour(0)
    assert view.actor_style("boundary", "all").colour == t.boundary_colour(1)

    view.highlight("region", "low")
    assert view.highlighted() == ("region", "low")
    assert view.actor_style("region", "low").opacity == 1.0
    assert view.actor_style("region", "high").opacity == t.OPACITY_DIMMED

    view.highlight("boundary", "bottom")
    assert view.actor_style("boundary", "bottom").width == t.LINE_WIDTH_SELECTED
    assert view.actor_style("region", "low").opacity == t.OPACITY

    view.highlight("", "")
    assert view.actor_style("boundary", "bottom").width == t.LINE_WIDTH


@pytest.mark.ui
def test_a_run_selection_highlights_nothing(qtbot, mesh):
    view = GeometryView()
    qtbot.addWidget(view)
    view.set_document(Document(source=None, mesh=mesh))
    view.highlight("run", "run 1")
    assert view.highlighted() == ("", "")


@pytest.mark.ui
def test_shape_outlines_are_drawn_when_there_is_a_scene(qtbot, tmp_path):
    document = open_document(EXAMPLE, tmp_path)
    view = GeometryView()
    qtbot.addWidget(view)
    view.set_document(document)
    assert view.actor_style("shape", "wall") is not None
    view.highlight("shape", "wall")
    assert view.actor_style("shape", "wall").colour == t.ACCENT
    assert view.actor_style("shape", "electrode").colour == t.SHAPE_OUTLINE


@pytest.mark.ui
def test_mesh_view_shows_the_edges_and_geometry_view_does_not():
    assert MeshView.show_edges is True
    assert GeometryView.show_edges is False


def test_capacitor_scene_helper_is_importable():
    assert capacitor_scene().shapes
