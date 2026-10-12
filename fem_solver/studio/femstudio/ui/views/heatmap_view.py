import numpy as np

from femstudio.core.results.result_set import ResultSet
from femstudio.ui.views.field_view import FieldView


class HeatmapView(FieldView):
    """The field as colour on the flat mesh, seen from above."""

    def _points(self, results: ResultSet, field: str, low: float, high: float) -> np.ndarray:
        nodes = results.mesh.nodes
        return np.column_stack([nodes, np.zeros(len(nodes))])

    def _show_camera(self) -> None:
        plotter = self._plotter
        plotter.view_xy()
        plotter.enable_parallel_projection()
        plotter.enable_image_style()
        plotter.reset_camera()
