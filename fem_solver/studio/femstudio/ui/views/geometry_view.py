from dataclasses import dataclass

import numpy as np
import pyvista as pv
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from femstudio.core.mesh.mesh_data import MeshData
from femstudio.core.project.document import Document
from femstudio.ui.theme import tokens as t

UNNAMED_KIND = "unnamed"


@dataclass(frozen=True)
class Style:
    colour: str
    opacity: float
    width: float


def surface_of(mesh: MeshData, triangle_ids: np.ndarray) -> pv.PolyData:
    """The triangles `triangle_ids` as a flat surface in the z = 0 plane."""
    points = np.column_stack([mesh.nodes, np.zeros(mesh.n_nodes)])
    triangles = mesh.triangles[triangle_ids]
    faces = np.column_stack([np.full(len(triangles), 3), triangles]).ravel()
    return pv.PolyData(points, faces)


def lines_of(mesh: MeshData, edge_ids: np.ndarray) -> pv.PolyData:
    """The edges `edge_ids` as line segments in the z = 0 plane."""
    points = np.column_stack([mesh.nodes, np.zeros(mesh.n_nodes)])
    edges = mesh.edges[edge_ids]
    cells = np.column_stack([np.full(len(edges), 2), edges]).ravel()
    return pv.PolyData(points, lines=cells)


def polyline_of(points_xy) -> pv.PolyData:
    points = np.column_stack([np.asarray(points_xy, dtype=float), np.zeros(len(points_xy))])
    return pv.lines_from_points(points)


def element_styles(
    shapes: list[str],
    regions: list[str],
    boundaries: list[str],
    selected: tuple[str, str],
    show_edges: bool = False,
) -> dict[tuple[str, str], Style]:
    """The look of every element: its own colour, with the selected one standing out."""
    kind, name = selected
    styles: dict[tuple[str, str], Style] = {}
    for index, region in enumerate(regions):
        if kind == "region":
            opacity = 1.0 if region == name else t.OPACITY_DIMMED
        else:
            opacity = t.OPACITY
        styles[("region", region)] = Style(t.region_colour(index), opacity, t.OUTLINE_WIDTH)
    for index, boundary in enumerate(boundaries):
        selected_here = kind == "boundary" and boundary == name
        dimmed = kind == "boundary" and not selected_here
        width = t.LINE_WIDTH_SELECTED if selected_here else t.LINE_WIDTH
        opacity = t.OPACITY_DIMMED if dimmed else 1.0
        styles[("boundary", boundary)] = Style(t.boundary_colour(index), opacity, width)
    for shape in shapes:
        highlighted = kind == "shape" and shape == name
        colour = t.ACCENT if highlighted else t.SHAPE_OUTLINE
        width = t.LINE_WIDTH_SELECTED if highlighted else t.OUTLINE_WIDTH
        styles[("shape", shape)] = Style(colour, 1.0, width)
    return styles


class GeometryView(QWidget):
    """Named regions filled, boundaries as coloured lines, shape outlines, seen from above."""

    show_edges = False

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._note = QLabel()
        self._note.setProperty("role", "note")
        self._note.setWordWrap(True)
        self._note.hide()
        layout.addWidget(self._note)
        self._document: Document | None = None
        self._selected: tuple[str, str] = ("", "")
        self._actors: dict[tuple[str, str], object] = {}
        self._drawn = False
        self._plotter = None
        try:
            from pyvistaqt import QtInteractor

            self._plotter = QtInteractor(self)
            self._plotter.set_background(t.STAGE)
            layout.addWidget(self._plotter.interactor)
        except Exception as error:  # no usable OpenGL: the window still opens
            note = QLabel(f"3D drawing is not available here: {error}")
            note.setObjectName("placeholder")
            layout.addWidget(note)

    @property
    def can_draw(self) -> bool:
        return self._plotter is not None

    def names(self) -> tuple[list[str], list[str], list[str]]:
        document = self._document
        if document is None:
            return [], [], []
        shapes = [s.name for s in document.scene.shapes] if document.scene else []
        return shapes, document.region_names, document.boundary_names

    def style(self, kind: str, name: str) -> Style:
        shapes, regions, boundaries = self.names()
        return element_styles(shapes, regions, boundaries, self._selected)[(kind, name)]

    def highlighted(self) -> tuple[str, str]:
        return self._selected

    def set_document(self, document: Document | None, reset_view: bool = True) -> None:
        """Redraw. After an edit (`reset_view` False) the camera and the highlight stay."""
        keep = not reset_view and self._plotter is not None and self._drawn
        camera = None
        if keep:
            camera = (self._plotter.camera_position, self._plotter.camera.parallel_scale)
        else:
            self._selected = ("", "")
        self._document = document
        self._actors = {}
        unmeshed = document is not None and document.mesh is None
        self._note.setText(f"Not meshed: {document.mesh_error}" if unmeshed else "")
        self._note.setVisible(unmeshed)
        if self._plotter is None:
            return
        self._plotter.clear()
        if document is not None:
            self._draw(document)
        self._plotter.view_xy()
        self._plotter.enable_parallel_projection()
        self._plotter.enable_image_style()
        if camera is None:
            self._plotter.reset_camera()
        else:
            self._plotter.camera_position = camera[0]
            self._plotter.camera.parallel_scale = camera[1]
        self._drawn = document is not None and bool(self._actors)
        self._plotter.render()

    def _add(self, key: tuple[str, str], poly: pv.PolyData, **options) -> None:
        if poly.n_cells == 0:
            return
        self._actors[key] = self._plotter.add_mesh(poly, name=f"{key[0]}:{key[1]}", **options)

    def note(self) -> str:
        return self._note.text()

    def _draw(self, document: Document) -> None:
        mesh = document.mesh
        shapes, regions, boundaries = self.names()
        styles = element_styles(shapes, regions, boundaries, self._selected)
        if mesh is None:
            regions, boundaries = [], []
        elif not mesh.regions and mesh.n_triangles:
            self._add(
                (UNNAMED_KIND, ""),
                surface_of(mesh, np.arange(mesh.n_triangles)),
                color=t.UNNAMED_FILL,
                show_edges=self.show_edges,
                edge_color=t.MESH_EDGE,
                line_width=t.OUTLINE_WIDTH,
                lighting=False,
            )
        for name in regions:
            ids = mesh.regions.get(name)
            if ids is None:
                continue
            style = styles[("region", name)]
            self._add(
                ("region", name),
                surface_of(mesh, ids),
                color=style.colour,
                opacity=style.opacity,
                show_edges=self.show_edges,
                edge_color=t.MESH_EDGE,
                line_width=t.OUTLINE_WIDTH,
                lighting=False,
            )
        for name in boundaries:
            ids = mesh.boundaries.get(name)
            if ids is None:
                continue
            style = styles[("boundary", name)]
            self._add(
                ("boundary", name),
                lines_of(mesh, ids),
                color=style.colour,
                opacity=style.opacity,
                line_width=style.width,
                lighting=False,
            )
        if document.scene is not None:
            for shape in document.scene.shapes:
                style = styles[("shape", shape.name)]
                self._add(
                    ("shape", shape.name),
                    polyline_of(shape.outline_points()),
                    color=style.colour,
                    line_width=style.width,
                    lighting=False,
                )

    def highlight(self, kind: str, name: str) -> None:
        """Make one element stand out; an empty kind clears it. Runs have nothing to show."""
        self._selected = (kind, name) if kind in ("shape", "region", "boundary") else ("", "")
        if self._plotter is None or self._document is None:
            return
        shapes, regions, boundaries = self.names()
        styles = element_styles(shapes, regions, boundaries, self._selected)
        for key, actor in self._actors.items():
            if key not in styles:
                continue
            style = styles[key]
            prop = actor.GetProperty()
            prop.SetColor(*pv.Color(style.colour).float_rgb)
            prop.SetOpacity(style.opacity)
            prop.SetLineWidth(style.width if key[0] != "region" else t.OUTLINE_WIDTH)
        self._plotter.render()

    def actor_style(self, kind: str, name: str) -> Style | None:
        """The look of the drawn actor itself, read back from the renderer."""
        actor = self._actors.get((kind, name))
        if actor is None:
            return None
        prop = actor.GetProperty()
        colour = pv.Color(prop.GetColor()).hex_rgb.lower()
        return Style(colour, round(prop.GetOpacity(), 6), prop.GetLineWidth())

    def close_plotter(self) -> None:
        if self._plotter is not None:
            self._plotter.close()
