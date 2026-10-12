import pytest
from femstudio.core.scene.boundary import BoundaryCondition
from PySide6.QtWidgets import QPushButton

pytestmark = pytest.mark.ui


@pytest.fixture
def panel(opened):
    return opened.properties.panel("Physics")


def select(window, kind, name):
    window.scene_dock.select(kind, name)


def test_a_region_shows_its_material_in_editable_fields(opened, panel):
    select(opened, "region", "glass")
    tensor = panel.widget("material").editor("epsilon")
    assert tensor.value() == 4.0
    assert panel.widget("apply").isEnabled()


def test_applying_a_region_changes_its_material_as_one_undoable_step(opened, panel):
    select(opened, "region", "glass")
    panel.widget("material").editor("epsilon").box(0, 0).set_value(6.0)
    panel.widget("material").editor("epsilon").box(1, 1).set_value(6.0)
    before = opened.document.mesh
    panel.widget("apply").click()
    assert opened.session.scene.region("glass").material == {"epsilon": 6.0}
    assert opened.scene_dock.rows()["region"][0] == ("glass", "epsilon 6")
    assert opened.document.mesh is before  # a physics edit does not re-mesh the preview
    assert opened.menu.edit_titles()[0] == "Undo edit glass"
    opened.session.undo()
    assert opened.session.scene.region("glass").material == {"epsilon": ((4.0, 0.0), (0.0, 4.0))}


def test_an_anisotropic_material_is_stored_as_a_matrix(opened, panel):
    select(opened, "region", "air")
    tensor = panel.widget("material").editor("epsilon")
    tensor.box(0, 1).set_value(0.25)
    panel.widget("apply").click()
    assert opened.session.scene.region("air").material["epsilon"] == ((1.0, 0.25), (0.25, 1.0))


def test_a_boundary_condition_is_changed_by_kind_and_values(opened, panel):
    select(opened, "boundary", "inner_electrode")
    condition = panel.widget("condition")
    assert condition.kind_name() == "dirichlet"
    condition.set_kind("robin")
    condition.form("robin").editor("kappa").setText("3")
    condition.form("robin").editor("u_ref").setText("2*x")
    panel.widget("apply").click()
    assert opened.session.scene.boundary("inner_electrode").condition == BoundaryCondition(
        "robin", {"kappa": "3", "u_ref": "2*x"}
    )
    assert opened.scene_dock.rows()["boundary"][0] == (
        "inner_electrode",
        "kappa 3 1/m, u_ref 2*x V",
    )


def test_a_boundary_can_be_given_no_condition(opened, panel):
    select(opened, "boundary", "inner_electrode")
    panel.widget("condition").set_kind(None)
    panel.widget("apply").click()
    assert opened.session.scene.boundary("inner_electrode").condition is None
    assert any(f.rule == "boundary-default" for f in opened.status.findings())


def test_an_expression_that_does_not_parse_is_kept_and_makes_run_unavailable(opened, panel):
    select(opened, "boundary", "inner_electrode")
    panel.widget("condition").form("dirichlet").editor("g").setText("5 *")
    panel.widget("apply").click()
    assert opened.session.scene.boundary("inner_electrode").condition.values == {"g": "5 *"}
    assert "1 error" in opened.status.texts()[0]
    assert not opened.workflow.run_enabled()
    assert "inner_electrode" in opened.workflow._run.toolTip()


def test_the_source_and_the_outer_edges_are_edited_with_nothing_selected(opened, panel):
    opened.scene_dock.clear_selection()
    assert opened.session.scene.default_boundary is None
    panel.widget("source").editor("rho").setText("exp(-r^2)")
    panel.widget("apply_source").click()
    assert opened.session.scene.source == {"rho": "exp(-r^2)"}
    panel.widget("outer").set_kind("dirichlet")
    panel.widget("apply_outer").click()
    assert opened.session.scene.default_boundary == BoundaryCondition("dirichlet", {"g": "0"})


def test_a_scene_with_unnamed_outer_edges_is_fixed_from_the_panel(window, tmp_path):
    from examples.capacitor import capacitor_scene
    from femstudio.core.scene.serialization import save_scene

    scene = capacitor_scene()
    scene.boundaries.pop()
    path = tmp_path / "scene.json"
    save_scene(scene, path)
    assert window.open_path(path)
    assert window.document.mesh is None
    assert not window.workflow.run_enabled()
    panel = window.properties.panel("Physics")
    window.scene_dock.clear_selection()
    panel.widget("outer").set_kind("dirichlet")
    panel.widget("apply_outer").click()
    assert window.document.mesh is not None
    assert "0 errors" in window.status.texts()[0]
    assert window.workflow.run_enabled()


def test_a_material_that_is_not_positive_definite_is_kept_and_reported(opened, panel):
    select(opened, "region", "glass")
    tensor = panel.widget("material").editor("epsilon")
    tensor.box(0, 1).set_value(9.0)
    panel.widget("apply").click()
    assert opened.session.scene.region("glass").material["epsilon"] == ((4.0, 9.0), (9.0, 4.0))
    assert any(f.rule == "material-tensor" for f in opened.status.findings())
    assert not opened.workflow.run_enabled()


def test_the_default_boundary_row_edits_the_outer_edges(window, tmp_path):
    from examples.capacitor import capacitor_scene
    from femstudio.core.scene.boundary import DEFAULT_BOUNDARY_NAME
    from femstudio.core.scene.serialization import save_scene

    scene = capacitor_scene()
    scene.boundaries.pop()
    scene.default_boundary = BoundaryCondition("dirichlet", {"g": "0"})
    path = tmp_path / "scene.json"
    save_scene(scene, path)
    assert window.open_path(path)
    panel = window.properties.panel("Physics")
    select(window, "boundary", DEFAULT_BOUNDARY_NAME)
    assert panel.rows() == [("kind", "Fixed potential"), ("g", "0 V")]
    panel.widget("outer").form("dirichlet").editor("g").setText("1")
    panel.widget("apply_outer").click()
    assert window.session.scene.default_boundary.values == {"g": "1"}


def test_the_panel_fits_the_dock_at_every_selection(opened, panel):
    dock_width = opened.properties.width()
    for kind, name in (
        ("region", "glass"),
        ("boundary", "inner_electrode"),
        ("shape", "wall"),
    ):
        select(opened, kind, name)
        assert panel.minimumSizeHint().width() <= dock_width - 20, (kind, name)


def test_the_editors_are_only_buttons_and_inputs_the_user_can_reach(opened, panel):
    select(opened, "region", "glass")
    buttons = [b for b in panel.findChildren(QPushButton) if b.isVisibleTo(panel)]
    assert [b.text() for b in buttons] == ["Apply"]
