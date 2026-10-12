import numpy as np

from femstudio.core.results.result_set import ResultSet
from femstudio.ui.theme import tokens as t
from femstudio.ui.views.field_view import FieldView, longest_side


def surface_heights(values: np.ndarray, low: float, high: float, extent: float) -> np.ndarray:
    """Height of each value: `low` sits at 0 and `high` at `extent`, beyond them it is clipped.

    Clipping matches the colours, which saturate at the ends of the range, and keeps a narrowed
    range from sending the surface out of the picture. Not-a-number stays flat.
    """
    heights = (np.asarray(values, dtype=float) - low) / (high - low) * extent
    return np.where(np.isfinite(heights), np.clip(heights, 0.0, extent), 0.0)


class SurfaceView(FieldView):
    """The field as a surface whose height is the value, coloured by the same value."""

    averaged = True  # a surface needs a height at every node

    def _points(self, results: ResultSet, field: str, low: float, high: float) -> np.ndarray:
        extent = t.SURFACE_HEIGHT * longest_side(results.mesh)
        heights = surface_heights(results.node_values(field), low, high, extent)
        return np.column_stack([results.mesh.nodes, heights])

    def _show_camera(self) -> None:
        plotter = self._plotter
        plotter.disable_parallel_projection()
        plotter.enable_trackball_style()
        plotter.view_isometric()
        plotter.reset_camera()
