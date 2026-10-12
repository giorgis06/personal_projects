import numpy as np
from femstudio.ui.views.surface_view import surface_heights


def test_the_low_end_of_the_range_is_flat_and_the_high_end_is_the_extent():
    heights = surface_heights([-2.0, 0.0, 2.0], -2.0, 2.0, 0.8)
    np.testing.assert_allclose(heights, [0.0, 0.4, 0.8])


def test_height_is_proportional_to_value():
    values = np.array([1.0, 2.0, 4.0])
    heights = surface_heights(values, 0.0, 4.0, 2.0)
    np.testing.assert_allclose(heights / values, 0.5)


def test_a_value_that_is_not_a_number_stays_flat():
    assert surface_heights([np.nan, np.inf], 0.0, 1.0, 1.0).tolist() == [0.0, 0.0]


def test_values_outside_the_range_are_held_at_its_ends():
    heights = surface_heights([-1.0, 3.0, 1e9], 0.0, 2.0, 1.0)
    assert heights.tolist() == [0.0, 1.0, 1.0]
