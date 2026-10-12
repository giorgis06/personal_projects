import pytest
from examples.capacitor import capacitor_scene
from femstudio.core.scene import editing
from femstudio.core.scene.history import History


@pytest.fixture
def scene():
    return capacitor_scene()


def test_nothing_to_undo_at_first():
    history = History()
    assert not history.can_undo and not history.can_redo
    assert history.undo_label is None


def test_undo_returns_the_scene_as_it_was_before_the_edit(scene):
    history = History()
    history.record(scene, "move wall")
    editing.update_shape(scene, "wall", radius=3.0)
    restored = history.undo(scene)
    assert restored.shape("wall").radius == 2.0
    assert scene.shape("wall").radius == 3.0
    assert history.can_redo and not history.can_undo


def test_redo_brings_the_edit_back(scene):
    history = History()
    history.record(scene, "move wall")
    editing.update_shape(scene, "wall", radius=3.0)
    restored = history.undo(scene)
    again = history.redo(restored)
    assert again.shape("wall").radius == 3.0
    assert history.undo_label == "move wall"


def test_a_new_edit_clears_the_redo_steps(scene):
    history = History()
    history.record(scene, "one")
    editing.update_shape(scene, "wall", radius=3.0)
    scene = history.undo(scene)
    history.record(scene, "two")
    assert not history.can_redo


def test_snapshots_keep_regions_pointing_at_their_own_shapes(scene):
    history = History()
    history.record(scene, "x")
    restored = history.undo(scene)
    leaf = restored.region("glass").area.operands[0]
    assert leaf is restored.shape("glass_outer")
    editing.update_shape(restored, "glass_outer", radius=0.9)
    assert restored.region("glass").area.operands[0].radius == 0.9


def test_snapshot_is_independent_of_later_edits(scene):
    history = History()
    history.record(scene, "x")
    editing.rename_shape(scene, "wall", "far")
    restored = history.undo(scene)
    assert [s.name for s in restored.shapes] == ["electrode", "glass_outer", "wall"]
    assert restored.boundary("outer_wall").curve.shape == "wall"


def test_the_oldest_steps_fall_off(scene):
    history = History(limit=3)
    for i in range(5):
        history.record(scene, f"step {i}")
    labels = []
    while history.can_undo:
        labels.append(history.undo_label)
        history.undo(scene)
    assert labels == ["step 4", "step 3", "step 2"]


def test_rollback_forgets_a_refused_edit_and_returns_the_snapshot(scene):
    history = History()
    history.record(scene, "refused")
    editing.update_shape(scene, "wall", radius=9.0)
    restored = history.rollback()
    assert not history.can_undo and not history.can_redo
    assert restored.shape("wall").radius == 2.0
