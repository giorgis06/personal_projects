import pytest
from femstudio.core.scene.boundary import BoundaryCondition
from femstudio.ui.panels.geometry import describe_area, describe_curve
from femstudio.ui.panels.mesh import MeshPanel
from femstudio.ui.panels.physics import PhysicsPanel
from femstudio.ui.panels.results import ResultsPanel
from femstudio.ui.panels.solve import SolvePanel


def test_curve_descriptions():
    from femstudio.core.scene.boundary import Between, Outline, Side

    assert describe_curve(Outline("wall")) == "outline of wall"
    assert describe_curve(Side("sq", "left")) == "side left of sq"
    assert describe_curve(Between("glass", "air")) == "between glass and air"


def test_area_description_nests_operations(document):
    scene = document.scene
    area = (scene.shape("wall") - scene.shape("glass_outer")) | scene.shape("electrode")
    assert describe_area(area) == "((wall - glass_outer) | electrode)"


@pytest.mark.ui
def test_physics_panel_shows_the_values_the_problem_type_asks_for(qtbot, session):
    panel = PhysicsPanel(session)
    qtbot.addWidget(panel)
    document = session.document
    panel.update_view(document, "region", "glass")
    assert panel.rows() == [("epsilon", "4")]
    panel.update_view(document, "boundary", "inner_electrode")
    assert panel.rows() == [("kind", "Fixed potential"), ("g", "5 V")]
    panel.update_view(document, "", "")
    assert panel.rows() == [("rho", "0 C/m^3"), ("outer edges", "must be named")]


@pytest.mark.ui
def test_physics_panel_shows_robin_fields_and_the_default_boundary(qtbot, session):
    scene = session.scene
    scene.boundaries[0].condition = BoundaryCondition("robin", {"kappa": "2", "u_ref": "5"})
    scene.default_boundary = BoundaryCondition("dirichlet", {"g": "0"})
    panel = PhysicsPanel(session)
    qtbot.addWidget(panel)
    document = session.document
    panel.update_view(document, "boundary", "inner_electrode")
    assert panel.rows() == [
        ("kind", "Coupled to a reference potential"),
        ("kappa", "2 1/m"),
        ("u_ref", "5 V"),
    ]
    panel.update_view(document, "", "")
    assert ("outer edges", "dirichlet") in panel.rows()


@pytest.mark.ui
def test_physics_panel_without_a_scene(qtbot, session, tmp_path):
    from femstudio.core.project.document import open_document
    from tests.ui.conftest import DATA

    panel = PhysicsPanel(session)
    qtbot.addWidget(panel)
    panel.update_view(open_document(DATA / "square.geo", tmp_path), "", "")
    assert panel.rows() == []


@pytest.mark.ui
def test_mesh_panel_counts(qtbot, session):
    panel = MeshPanel(session)
    qtbot.addWidget(panel)
    document = session.document
    panel.update_view(document, "", "")
    rows = dict(panel.rows())
    assert rows["nodes"] == str(document.mesh.n_nodes)
    assert rows["triangles"] == str(document.mesh.n_triangles)
    assert rows["element size"] == "0.1"
    assert rows["glass"] == f"{len(document.mesh.regions['glass'])} triangles"
    panel.update_view(None, "", "")
    assert panel.rows() == [("mesh", "none")]


@pytest.mark.ui
def test_solve_panel_names_the_backend_and_its_availability(qtbot, session):
    panel = SolvePanel(session)
    qtbot.addWidget(panel)
    panel.set_backend("mock")
    rows = dict(panel.rows())
    assert rows["backend"] == "mock" and rows["available"] == "yes"
    assert rows["method"] == "cg"
    assert panel._tolerance.text() == "1e-10"
    assert panel._iterations.value() == 10000


@pytest.mark.ui
def test_results_panel_says_there_is_no_result_yet(qtbot, document):
    panel = ResultsPanel()
    qtbot.addWidget(panel)
    panel.update_view(document, "", "")
    assert panel.text() == "No result yet."
    panel.update_view(document, "run", "run 1")
    assert panel.text() == "run 1: no result loaded."
