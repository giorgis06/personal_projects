import numpy as np
import pytest
from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.results.field import Field
from femstudio.core.results.result_set import ResultSet
from femstudio.ui.results_state import ResultsState
from femstudio.ui.theme import tokens as t

pytestmark = pytest.mark.ui


def state_with(values, name="u"):
    nodes = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=float)
    mesh = MeshData(
        nodes, np.arange(1, 5), np.array([[0, 1, 2], [1, 3, 2]]), np.empty((0, 2), int), {}, {}
    )
    results = ResultSet(1, mesh, {name: Field(name, np.asarray(values, float), "V", "node")}, {})
    state = ResultsState()
    state._results = results
    state._display = state._display.__class__(field=name)
    return state


def test_automatic_range_is_the_fields_range():
    assert state_with([1.0, 2.0, 3.0, 5.0]).colour_range() == (1.0, 5.0)


def test_a_field_that_changes_sign_is_centred_on_zero_with_the_diverging_map():
    state = state_with([-1.0, 0.0, 2.0, 3.0])
    assert state.colour_range() == (-1.0, 3.0)
    state.set_colour_map(t.SIGN_CHANGING_MAP)
    assert state.colour_range() == (-3.0, 3.0)


def test_a_field_with_one_value_still_gets_a_range():
    low, high = state_with([4.0, 4.0, 4.0, 4.0]).colour_range()
    assert low < 4.0 < high
    low, high = state_with([0.0, 0.0, 0.0, 0.0]).colour_range()
    assert low < 0.0 < high


def test_a_manual_range_is_used_as_given_and_automatic_takes_it_back():
    state = state_with([1.0, 2.0, 3.0, 5.0])
    state.set_range(0.0, 10.0)
    assert state.colour_range() == (0.0, 10.0)
    state.use_automatic_range()
    assert state.colour_range() == (1.0, 5.0)


@pytest.mark.parametrize(
    "low,high", [(1.0, 1.0), (2.0, 1.0), (float("nan"), 1.0), (0.0, float("inf"))]
)
def test_a_range_that_is_empty_reversed_or_not_finite_is_refused(low, high):
    state = state_with([1.0, 2.0, 3.0, 5.0])
    with pytest.raises(ValueError):
        state.set_range(low, high)
    assert state.display.auto_range


def test_unknown_names_are_refused():
    state = state_with([1.0, 2.0, 3.0, 5.0])
    with pytest.raises(KeyError):
        state.set_field("nope")
    with pytest.raises(KeyError):
        state.set_colour_map("rainbow")


def test_changing_the_field_goes_back_to_the_automatic_range():
    state = state_with([1.0, 2.0, 3.0, 5.0])
    state.set_range(0.0, 10.0)
    state._results.fields["w"] = Field("w", np.array([0.0, 1.0, 2.0, 3.0]), "J")
    state.set_field("w")
    assert state.display.auto_range
    assert state.colour_range() == (0.0, 3.0)


def test_signals_are_sent_only_for_a_change(qtbot):
    state = state_with([1.0, 2.0, 3.0, 5.0])
    seen = []
    state.displayChanged.connect(lambda: seen.append("display"))
    state.set_mesh_overlay(False)
    state.set_colour_map(t.DEFAULT_COLOUR_MAP)
    assert seen == []
    state.set_mesh_overlay(True)
    assert seen == ["display"]


def test_rounding_noise_at_the_end_of_a_range_counts_as_zero():
    state = state_with([-6.87e-16, 1.0, 2.0, 5.0])
    assert state.colour_range() == (0.0, 5.0)
    state.set_colour_map(t.SIGN_CHANGING_MAP)
    assert state.colour_range() == (0.0, 5.0)  # the field does not change sign


def test_a_small_negative_value_that_is_real_is_kept():
    assert state_with([-0.01, 1.0, 2.0, 5.0]).colour_range() == (-0.01, 5.0)
