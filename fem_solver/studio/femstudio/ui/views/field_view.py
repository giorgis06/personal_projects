import numpy as np
import pyvista as pv
from vtkmodules.vtkRenderingCore import vtkCellPicker

from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.results.probe import locate
from femstudio.core.results.result_set import ResultSet
from femstudio.ui.results_state import ResultsState
from femstudio.ui.theme import tokens as t
from femstudio.ui.views.plotter_view import PlotterView

NO_RESULT = "No result yet. Run a solve to see the field here."
FIELD_ACTOR = "field"
PROBE_ACTOR = "probe"
VALUES = "values"
TITLE_ACTOR = "bar_title"


def longest_side(mesh: MeshData) -> float:
    if mesh.n_nodes == 0:
        return 1.0
    return float(np.ptp(mesh.nodes, axis=0).max()) or 1.0


class FieldView(PlotterView):
    """The field of the run being looked at, coloured by value, with a colour bar and a probe.

    The Heatmap and the 3D surface differ in the points they draw and in how the camera sees
    them; everything the user chooses lives in the shared `ResultsState`.
    """

    averaged = False  # colour a per-triangle field from node averages instead of flat triangles

    def __init__(self, results: ResultsState) -> None:
        super().__init__(lazy=True)
        self._state = results
        self._poly: pv.PolyData | None = None
        self._viewed = False
        results.resultChanged.connect(lambda: self._draw(reset_camera=True))
        results.displayChanged.connect(lambda: self._draw(reset_camera=False))
        results.probeChanged.connect(self._draw_probe)
        self._update_note()

    def _update_note(self) -> None:
        if self._state.results is None:
            self._set_note(self._state.message or NO_RESULT)
        else:
            self._set_note("")

    def _plotter_ready(self) -> None:
        if self._plotter is not None and not self._headless():
            self._plotter.track_click_position(self._on_click, side="left", double=True)
        self._draw(reset_camera=True)

    # -- what a subclass decides

    def _points(self, results: ResultSet, field: str, low: float, high: float) -> np.ndarray:
        """The (N, 3) position of every node."""
        raise NotImplementedError

    def _show_camera(self) -> None:
        raise NotImplementedError

    # -- what the tests and the window read

    def shown(self) -> tuple[int, str, str] | None:
        """(run number, field, colour map) now drawn, or None when no result is shown."""
        results = self._state.results
        if results is None or self._poly is None:
            return None
        return results.run_number, self._state.display.field, self._state.display.colour_map

    def drawn_values(self) -> np.ndarray | None:
        """The numbers the colours come from: per node or per triangle."""
        return None if self._poly is None else np.asarray(self._poly[VALUES])

    def drawn_range(self) -> tuple[float, float] | None:
        actor = self._actor(FIELD_ACTOR)
        if actor is None:
            return None
        low, high = actor.GetMapper().GetScalarRange()
        return float(low), float(high)

    def bar_title(self) -> str | None:
        """The text above the colour bar: the field and its unit."""
        actor = self._actor(TITLE_ACTOR)
        if actor is None:
            return None
        return next((text for i in range(4) if (text := actor.GetText(i))), None)

    def bar_count(self) -> int:
        return len(self._plotter.scalar_bars) if self._plotter is not None else 0

    def probe_position(self) -> tuple[float, float, float] | None:
        actor = self._actor(PROBE_ACTOR)
        if actor is None:
            return None
        return tuple(float(v) for v in actor.GetMapper().GetInput().GetPoint(0))

    def show_edges(self) -> bool:
        actor = self._actor(FIELD_ACTOR)
        return bool(actor is not None and actor.GetProperty().GetEdgeVisibility())

    # -- drawing

    @staticmethod
    def _headless() -> bool:
        from PySide6.QtGui import QGuiApplication

        from femstudio.ui.views.plotter_view import HEADLESS_PLATFORMS

        return QGuiApplication.platformName() in HEADLESS_PLATFORMS

    def _actor(self, name: str):
        if self._plotter is None:
            return None
        return self._plotter.renderer.actors.get(name)

    def _release(self) -> None:
        self._poly = None

    def _draw(self, reset_camera: bool) -> None:
        self._update_note()
        plotter = self._plotter
        if plotter is None:
            return
        keep = None
        if not reset_camera and self._viewed:
            keep = (plotter.camera_position, plotter.camera.parallel_scale)
        plotter.clear()
        self._poly = None
        results = self._state.results
        if results is None:
            self._viewed = False
            plotter.render()
            return
        display = self._state.display
        low, high = self._state.colour_range()
        mesh = results.mesh
        faces = np.column_stack([np.full(mesh.n_triangles, 3), mesh.triangles]).ravel()
        poly = pv.PolyData(self._points(results, display.field, low, high), faces)
        if results.location(display.field) == "triangle" and not self.averaged:
            poly.cell_data[VALUES] = results.scalars(display.field)
        else:
            poly.point_data[VALUES] = results.node_values(display.field)
        self._poly = poly
        title = results.label(display.field)
        unit = results.unit(display.field)
        plotter.add_mesh(
            poly,
            scalars=VALUES,
            cmap=display.colour_map,
            clim=(low, high),
            show_edges=display.mesh_overlay,
            edge_color=t.MESH_EDGE,
            line_width=t.OUTLINE_WIDTH,
            nan_color=t.UNNAMED_FILL,
            lighting=False,
            name=FIELD_ACTOR,
            scalar_bar_args={
                "title": " ",  # the title is its own text: the bar's would cover its top label
                "vertical": True,
                "position_x": t.COLOUR_BAR_X,
                "position_y": t.COLOUR_BAR_Y,
                "width": t.COLOUR_BAR_WIDTH,
                "height": t.COLOUR_BAR_HEIGHT,
                "n_labels": t.COLOUR_BAR_LABELS,
                "fmt": t.COLOUR_BAR_FORMAT,
                "color": t.INK,
                "title_font_size": t.COLOUR_BAR_FONT,
                "label_font_size": t.COLOUR_BAR_FONT,
            },
        )
        plotter.add_text(
            f"{title} [{unit}]" if unit else title,
            position="upper_right",
            font_size=t.COLOUR_BAR_TITLE_FONT,
            color=t.INK,
            name=TITLE_ACTOR,
        )
        if keep is None:
            self._show_camera()
        else:
            plotter.camera_position = keep[0]
            plotter.camera.parallel_scale = keep[1]
        self._viewed = True
        self._draw_probe(render=False)
        plotter.render()

    def _draw_probe(self, render: bool = True) -> None:
        plotter = self._plotter
        if plotter is None:
            return
        plotter.remove_actor(PROBE_ACTOR, render=False)
        results, poly, probe = self._state.results, self._poly, self._state.probe
        if results is not None and poly is not None and probe is not None:
            found = locate(results.mesh, *probe)
            if found is not None:
                triangle, weights = found
                corners = results.mesh.triangles[triangle]
                z = float(weights @ poly.points[corners, 2])
                z += t.PROBE_LIFT * longest_side(results.mesh)
                plotter.add_points(
                    np.array([[probe[0], probe[1], z]]),
                    color=t.PROBE_COLOUR,
                    point_size=t.PROBE_SIZE,
                    render_points_as_spheres=True,
                    name=PROBE_ACTOR,
                    reset_camera=False,
                )
        if render:
            plotter.render()

    # -- picking

    def _on_click(self, position) -> None:
        self.pick(float(position[0]), float(position[1]))

    def pick(self, display_x: float, display_y: float) -> bool:
        """Put the probe where the drawn field is under a display position; False if none."""
        if self._plotter is None or self._poly is None:
            return False
        picker = vtkCellPicker()
        picker.SetTolerance(0.0005)
        if not picker.Pick(display_x, display_y, 0.0, self._plotter.renderer):
            return False
        x, y, _ = picker.GetPickPosition()
        self._state.set_probe(x, y)
        return True
