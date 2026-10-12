import pytest

pytestmark = pytest.mark.ui


@pytest.fixture
def mesh_panel(opened):
    return opened.properties.panel("Mesh")


@pytest.fixture
def solve_panel(opened):
    return opened.properties.panel("Solve")


def test_the_mesh_panel_shows_the_element_size_in_use(opened, mesh_panel):
    assert mesh_panel.size_text() == "0.1"
    assert dict(mesh_panel.rows())["element size"] == "0.1"


def test_a_new_element_size_re_meshes_the_preview(opened, mesh_panel):
    coarse = opened.document.mesh.n_triangles
    mesh_panel.set_size_text("0.2")
    mesh_panel.apply()
    assert opened.document.size == 0.2
    assert opened.document.mesh.n_triangles < coarse
    assert opened.session.mesh_size == 0.2
    assert dict(mesh_panel.rows())["element size"] == "0.2"
    assert opened.status.texts()[3] == "h = 0.2"
    assert not opened.session.dirty  # the size is a setting, not an edit of the scene


def test_the_default_size_comes_back(opened, mesh_panel):
    mesh_panel.set_size_text("0.2")
    mesh_panel.apply()
    mesh_panel.use_default()
    assert opened.document.size == 0.1
    assert opened.session.mesh_size is None
    assert mesh_panel.size_text() == "0.1"


def test_a_size_that_is_not_a_number_is_refused_in_the_panel(opened, mesh_panel):
    before = opened.document.mesh
    mesh_panel.set_size_text("fine")
    mesh_panel.apply()
    assert mesh_panel.message() == "'fine' is not a number"
    assert opened.document.mesh is before


@pytest.mark.parametrize("text", ["0", "-1", "nan", "1e-9"])
def test_a_size_the_mesher_cannot_use_is_refused_and_the_mesh_is_kept(opened, mesh_panel, text):
    before = opened.document.mesh
    mesh_panel.set_size_text(text)
    mesh_panel.apply()
    assert "element size" in mesh_panel.message()
    assert opened.document.mesh is before
    assert opened.session.mesh_size is None


def test_the_chosen_size_is_the_size_a_run_uses(qtbot, opened, mesh_panel):
    mesh_panel.set_size_text("0.2")
    mesh_panel.apply()
    plan = opened.session.plan_run()
    assert plan.size == 0.2


def test_the_size_survives_geometry_edits_and_goes_with_the_scene(opened, mesh_panel):
    mesh_panel.set_size_text("0.2")
    mesh_panel.apply()
    opened.properties.panel("Geometry").add_item("circle")
    assert opened.document.size == 0.2
    opened.new_scene()
    assert opened.session.mesh_size is None


def test_solver_settings_are_edited_and_used_by_the_next_run(opened, solve_panel):
    solve_panel._tolerance.setText("1e-6")
    solve_panel._iterations.setValue(500)
    solve_panel.apply()
    settings = opened.session.settings
    assert (settings.tolerance, settings.max_iterations) == (1e-6, 500)
    assert solve_panel._tolerance.text() == "1e-06"
    assert opened.session.plan_run().settings == settings


@pytest.mark.parametrize("text", ["fast", "0", "-1", "nan"])
def test_unusable_solver_settings_are_refused(opened, solve_panel, text):
    solve_panel._tolerance.setText(text)
    solve_panel.apply()
    assert solve_panel.message() != ""
    assert opened.session.settings.tolerance == 1e-10


def test_the_solve_panel_follows_the_backend_choice(opened, solve_panel, monkeypatch, tmp_path):
    monkeypatch.setenv("FEM_EXECUTABLE", str(tmp_path / "missing"))
    opened.workflow.set_backend("fem")
    rows = dict(solve_panel.rows())
    assert rows["backend"] == "fem" and rows["available"] == "no"
    opened.workflow.set_backend("mock")
    assert dict(solve_panel.rows())["available"] == "yes"
