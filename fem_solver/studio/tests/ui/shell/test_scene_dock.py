import pytest
from femstudio.core.scene.boundary import Between, Boundary, BoundaryCondition, Outline
from femstudio.core.scene.region import Region
from femstudio.core.scene.shapes import Circle, Polygon, Rectangle
from femstudio.physics import registry
from femstudio.ui.shell.scene_dock import (
    SceneDock,
    boundary_summary,
    region_summary,
    shape_summary,
)
from femstudio.ui.theme import tokens as t

PROBLEM = registry.get("electrostatics")


def test_shape_summaries():
    assert shape_summary(Circle("c", (0.0, 0.0), 0.25)) == "r 0.25"
    assert shape_summary(Rectangle("r", (0.0, 0.0), 2.0, 1.5)) == "2 x 1.5"
    assert shape_summary(Polygon("p", ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)))) == "3 points"


def test_region_summaries_come_from_the_problem_types_fields():
    iso = Region("a", Circle("c", (0.0, 0.0), 1.0), {"epsilon": ((4.0, 0.0), (0.0, 4.0))})
    aniso = Region("a", Circle("c", (0.0, 0.0), 1.0), {"epsilon": ((2.0, 0.5), (0.5, 1.0))})
    scalar = Region("a", Circle("c", (0.0, 0.0), 1.0), {"epsilon": 2.5})
    assert region_summary(iso, PROBLEM) == "epsilon 4"
    assert region_summary(aniso, PROBLEM) == "epsilon tensor"
    assert region_summary(scalar, PROBLEM) == "epsilon 2.5"


@pytest.mark.parametrize(
    ("condition", "text"),
    [
        (BoundaryCondition("dirichlet", {"g": "5"}), "5 V"),
        (BoundaryCondition("neumann", {"g": "2"}), "2 C/m^2"),
        (BoundaryCondition("robin", {"kappa": "2", "u_ref": "5"}), "kappa 2 1/m, u_ref 5 V"),
        (None, "none"),
    ],
)
def test_boundary_summaries_carry_the_units(condition, text):
    assert boundary_summary(Boundary("b", Outline("c"), condition), PROBLEM) == text


def test_an_interface_without_a_condition_is_continuous():
    assert boundary_summary(Boundary("i", Between("a", "b")), PROBLEM) == "continuous"


@pytest.mark.ui
def test_capacitor_is_listed_by_name_with_values(qtbot, document):
    dock = SceneDock()
    qtbot.addWidget(dock)
    dock.set_document(document, PROBLEM)
    assert dock.rows() == {
        "shape": [("electrode", "r 0.2"), ("glass_outer", "r 0.5"), ("wall", "r 2")],
        "region": [("glass", "epsilon 4"), ("air", "epsilon 1")],
        "boundary": [("inner_electrode", "5 V"), ("outer_wall", "0 V")],
        "run": [],
    }


@pytest.mark.ui
def test_swatches_use_the_palette_in_scene_order(qtbot, document):
    dock = SceneDock()
    qtbot.addWidget(dock)
    dock.set_document(document, PROBLEM)
    assert dock.swatches("region") == [t.region_colour(0), t.region_colour(1)]
    assert dock.swatches("boundary") == [t.boundary_colour(0), t.boundary_colour(1)]


@pytest.mark.ui
def test_selecting_a_row_reports_its_kind_and_name(qtbot, document):
    dock = SceneDock()
    qtbot.addWidget(dock)
    dock.set_document(document, PROBLEM)
    with qtbot.waitSignal(dock.selectionChanged) as signal:
        dock.select("region", "glass")
    assert signal.args == ["region", "glass"]
    with qtbot.waitSignal(dock.selectionChanged) as signal:
        dock.select("boundary", "outer_wall")
    assert signal.args == ["boundary", "outer_wall"]
    with qtbot.waitSignal(dock.selectionChanged) as signal:
        dock.clear_selection()
    assert signal.args == ["", ""]


@pytest.mark.ui
def test_selecting_a_name_that_is_not_there(qtbot, document):
    dock = SceneDock()
    qtbot.addWidget(dock)
    dock.set_document(document, PROBLEM)
    with pytest.raises(KeyError):
        dock.select("region", "vacuum")


@pytest.mark.ui
def test_a_mesh_without_a_scene_lists_its_named_groups(qtbot, tmp_path):
    from femstudio.core.project.document import open_document
    from tests.ui.conftest import DATA

    document = open_document(DATA / "two_materials.geo", tmp_path)
    dock = SceneDock()
    qtbot.addWidget(dock)
    dock.set_document(document, None)
    rows = dock.rows()
    assert rows["shape"] == []
    assert {name for name, _ in rows["region"]} == {"glass", "air"}
    assert all(summary.endswith("triangles") for _, summary in rows["region"])
    assert {name for name, _ in rows["boundary"]} == {"outer", "interface"}


@pytest.mark.ui
def test_closing_the_document_empties_the_tree(qtbot, document):
    dock = SceneDock()
    qtbot.addWidget(dock)
    dock.set_document(document, PROBLEM)
    dock.set_document(None, None)
    assert all(rows == [] for rows in dock.rows().values())


@pytest.mark.ui
def test_runs_are_listed_newest_first_with_their_time_or_state(qtbot, tmp_path):
    from examples.capacitor import capacitor_scene
    from femstudio.backends import registry as backends
    from femstudio.core.project.document import open_document
    from femstudio.core.project.project import Project

    project = Project.create(tmp_path / "proj", capacitor_scene())
    first = project.new_run()
    first.execute(project.load_scene(), PROBLEM, backends.get("mock"), size=0.3)
    project.new_run()
    document = open_document(tmp_path / "proj", tmp_path)

    dock = SceneDock()
    qtbot.addWidget(dock)
    dock.set_document(document, PROBLEM)
    runs = dock.rows()["run"]
    assert [name for name, _ in runs] == ["run 2", "run 1"]
    assert runs[0][1] == "created"
    assert runs[1][1].endswith(" s")
