import pytest
from examples.capacitor import capacitor_scene
from femstudio.core.scene import editing
from femstudio.core.scene.serialization import load_scene
from femstudio.ui.session import UNTITLED, Session
from tests.ui.conftest import EXAMPLE

pytestmark = pytest.mark.ui


@pytest.fixture
def session():
    session = Session()
    yield session
    session.close()


def test_opening_a_scene_announces_the_document_and_resets_the_view(qtbot, session):
    with qtbot.waitSignal(session.documentChanged) as signal:
        assert session.open_path(EXAMPLE)
    document, reset_view = signal.args
    assert document.scene == capacitor_scene() and reset_view is True
    assert not session.dirty and not session.history.can_undo


def test_an_edit_is_announced_without_a_view_reset_and_marks_the_scene_dirty(qtbot, session):
    session.open_path(EXAMPLE)
    with qtbot.waitSignal(session.documentChanged) as signal:
        session.edit("move", lambda scene: editing.update_shape(scene, "wall", radius=2.5))
    assert signal.args[1] is False
    assert session.dirty and session.history.can_undo
    assert session.scene.shape("wall").radius == 2.5


def test_a_refused_edit_is_reported_and_leaves_no_trace(qtbot, session):
    session.open_path(EXAMPLE)
    with qtbot.waitSignal(session.editRefused) as signal:
        result = session.edit(
            "rename", lambda scene: editing.rename_shape(scene, "wall", "electrode")
        )
    assert result is None and "already exists" in signal.args[0]
    assert not session.dirty and not session.history.can_undo
    assert session.scene == capacitor_scene()


def test_a_refused_edit_that_changed_something_first_is_rolled_back(session):
    session.open_path(EXAMPLE)

    def half_done(scene):
        editing.update_shape(scene, "wall", radius=9.0)
        editing.rename_shape(scene, "wall", "electrode")

    assert session.edit("both", half_done) is None
    assert session.scene.shape("wall").radius == 2.0


def test_undo_and_redo_walk_the_history(session):
    session.open_path(EXAMPLE)
    session.edit("one", lambda scene: editing.update_shape(scene, "wall", radius=3.0))
    session.edit("two", lambda scene: editing.update_shape(scene, "wall", radius=4.0))
    session.undo()
    assert session.scene.shape("wall").radius == 3.0
    session.undo()
    assert session.scene.shape("wall").radius == 2.0
    session.redo()
    assert session.scene.shape("wall").radius == 3.0
    assert session.history.undo_label == "one"


def test_undo_with_nothing_to_undo_is_harmless(session):
    session.open_path(EXAMPLE)
    session.undo()
    session.redo()
    assert session.scene == capacitor_scene()


def test_editing_with_no_document(qtbot, session):
    with qtbot.waitSignal(session.editRefused) as signal:
        assert session.edit("x", lambda scene: None) is None
    assert "no scene" in signal.args[0]


def test_a_mesh_only_document_has_no_scene_to_edit(qtbot, session, tmp_path):
    from tests.ui.conftest import DATA

    session.open_path(DATA / "square.geo")
    with qtbot.waitSignal(session.editRefused):
        session.edit("x", lambda scene: None)


def test_new_scene_is_untitled_and_empty(session):
    session.new_scene("electrostatics")
    assert session.document.source == UNTITLED
    assert session.scene.shapes == [] and session.document.mesh is None


def test_save_to_a_path_and_read_it_back(session, tmp_path):
    session.open_path(EXAMPLE)
    session.edit("move", lambda scene: editing.update_shape(scene, "wall", radius=2.5))
    target = tmp_path / "out.scene.json"
    assert session.save(target)
    assert load_scene(target).shape("wall").radius == 2.5
    assert not session.dirty and session.document.source == target


def test_save_into_a_project_writes_its_scene_file(session, tmp_path):
    from femstudio.core.project.project import Project

    Project.create(tmp_path / "proj", capacitor_scene())
    session.open_path(tmp_path / "proj")
    session.edit("move", lambda scene: editing.update_shape(scene, "wall", radius=2.5))
    assert session.save()
    assert Project.open(tmp_path / "proj").load_scene().shape("wall").radius == 2.5


def test_save_refuses_a_name_that_is_not_json(qtbot, session, tmp_path):
    session.open_path(EXAMPLE)
    with qtbot.waitSignal(session.errorRaised) as signal:
        assert session.save(tmp_path / "scene.txt") is False
    assert "json" in signal.args[1]


def test_opening_a_failing_file_keeps_the_current_document(qtbot, session, tmp_path):
    session.open_path(EXAMPLE)
    bad = tmp_path / "bad.json"
    bad.write_text("{ nope")
    with qtbot.waitSignal(session.errorRaised):
        assert session.open_path(bad) is False
    assert session.scene == capacitor_scene()


def test_edits_that_make_the_scene_unmeshable_still_show_the_scene(session):
    session.open_path(EXAMPLE)
    session.edit("drop", lambda scene: editing.remove_boundary(scene, "outer_wall"))
    assert session.document.mesh is None
    assert "named by no boundary" in session.document.mesh_error
    session.undo()
    assert session.document.mesh is not None


def test_an_unexpected_failure_inside_an_edit_rolls_back_and_is_raised(session):
    session.open_path(EXAMPLE)

    def broken(scene):
        editing.update_shape(scene, "wall", radius=9.0)
        raise RuntimeError("bug")

    with pytest.raises(RuntimeError, match="bug"):
        session.edit("broken", broken)
    assert session.scene.shape("wall").radius == 2.0
    assert not session.history.can_undo and not session.dirty


def test_an_untitled_scene_cannot_be_saved_without_a_name(qtbot, session, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session.new_scene("electrostatics")
    with qtbot.waitSignal(session.errorRaised) as signal:
        assert session.save() is False
    assert "choose a name" in signal.args[1]
    assert not (tmp_path / "untitled.scene.json").exists()
