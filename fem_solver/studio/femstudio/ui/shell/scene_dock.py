from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import QDockWidget, QTreeWidget, QTreeWidgetItem

from femstudio.core.project.document import Document
from femstudio.core.results.reader import ResultError, read_run_info
from femstudio.core.scene.boundary import DEFAULT_BOUNDARY_NAME, Between, Boundary, Outline
from femstudio.core.scene.shapes import Circle, Polygon, Rectangle
from femstudio.physics.base import ProblemType
from femstudio.ui.theme import tokens as t
from femstudio.ui.theme import zoom
from femstudio.ui.theme.stylesheet import resolve_fonts
from femstudio.ui.widgets.dock_title import DockTitle
from femstudio.ui.widgets.readouts import format_value

GROUPS = (("shape", "Shapes"), ("region", "Regions"), ("boundary", "Boundaries"), ("run", "Runs"))
KIND_ROLE = Qt.ItemDataRole.UserRole
NAME_ROLE = Qt.ItemDataRole.UserRole + 1
COLOUR_ROLE = Qt.ItemDataRole.UserRole + 2


def shape_summary(shape) -> str:
    if isinstance(shape, Circle):
        return f"r {shape.radius:g}"
    if isinstance(shape, Rectangle):
        return f"{shape.width:g} x {shape.height:g}"
    if isinstance(shape, Polygon):
        return f"{len(shape.points)} points"
    return ""


def region_summary(region, problem_type: ProblemType | None) -> str:
    names = (
        [f.name for f in problem_type.material_fields] if problem_type else list(region.material)
    )
    return ", ".join(
        f"{n} {format_value(region.material[n])}" for n in names if n in region.material
    )


def boundary_summary(boundary, problem_type: ProblemType | None) -> str:
    condition = boundary.condition
    if condition is None:
        return "continuous" if isinstance(boundary.curve, Between) else "none"
    kind = problem_type.boundary_kind(condition.kind) if problem_type else None
    fields = kind.fields if kind else ()
    if len(fields) == 1:
        spec = fields[0]
        return f"{format_value(condition.values.get(spec.name, ''))} {spec.unit}".strip()
    parts = []
    for spec in fields:
        parts.append(f"{spec.name} {format_value(condition.values.get(spec.name, ''))} {spec.unit}")
    return ", ".join(part.strip() for part in parts) or condition.kind


def run_summary(run) -> str:
    if run.state != "success":
        return run.state
    try:
        total = sum(read_run_info(run.result_dir).timings.values())
    except ResultError:
        return run.state
    return f"{total:.2f} s"


def _swatch(colour: str) -> QIcon:
    size = zoom.px(t.SWATCH)
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(colour))
    return QIcon(pixmap)


class SceneDock(QDockWidget):
    """A tree of the shapes, regions, boundaries and runs, by name with a short value."""

    selectionChanged = Signal(str, str)  # kind, name; both empty when nothing is selected

    def __init__(self) -> None:
        super().__init__("Scene")
        self.setObjectName("sceneDock")
        self.setTitleBarWidget(DockTitle("Scene", self))
        self._mono = resolve_fonts(zoom.current())[1]
        self._tree = QTreeWidget()
        self._tree.setObjectName("sceneTree")
        self._tree.setColumnCount(2)
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(False)
        self._tree.header().setStretchLastSection(False)
        self._tree.header().setSectionResizeMode(0, self._tree.header().ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(1, self._tree.header().ResizeMode.ResizeToContents)
        self._tree.currentItemChanged.connect(self._on_current_changed)
        self.setWidget(self._tree)
        self._groups: dict[str, QTreeWidgetItem] = {}
        self._build_groups()
        self.apply_zoom()

    def apply_zoom(self) -> None:
        """Resize indentation, swatches and the value font to the current zoom."""
        self._tree.setIndentation(zoom.px(t.TREE_INDENT))
        size = zoom.px(t.SWATCH)
        self._tree.setIconSize(QSize(size, size))
        self._mono = resolve_fonts(zoom.current())[1]
        for group in self._groups.values():
            for index in range(group.childCount()):
                item = group.child(index)
                item.setFont(1, self._mono)
                colour = item.data(0, COLOUR_ROLE)
                if colour is not None:
                    item.setIcon(0, _swatch(colour))

    def _build_groups(self) -> None:
        self._tree.clear()
        self._groups = {}
        for kind, title in GROUPS:
            item = QTreeWidgetItem([title, ""])
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._tree.addTopLevelItem(item)
            item.setExpanded(True)
            self._groups[kind] = item

    def _add(self, kind: str, name: str, summary: str, colour: str | None = None) -> None:
        item = QTreeWidgetItem([name, summary])
        item.setData(0, KIND_ROLE, kind)
        item.setData(0, NAME_ROLE, name)
        item.setData(0, COLOUR_ROLE, colour)
        item.setFont(1, self._mono)
        item.setForeground(1, QColor(t.MUTED))
        item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if colour is not None:
            item.setIcon(0, _swatch(colour))
        self._groups[kind].addChild(item)

    def selected(self) -> tuple[str, str]:
        item = self._tree.currentItem()
        if item is None or item.data(0, KIND_ROLE) is None:
            return ("", "")
        return (item.data(0, KIND_ROLE), item.data(0, NAME_ROLE))

    def set_document(
        self,
        document: Document | None,
        problem_type: ProblemType | None,
        keep_selection: bool = False,
        runs=None,
    ) -> None:
        """Rebuild the tree; `keep_selection` re-selects the selected row if it is still there.

        `runs` are the runs to list when the document is not a project (a scratch project's).
        """
        previous = self.selected() if keep_selection else ("", "")
        self._tree.blockSignals(True)
        self._build_groups()
        if document is not None:
            self._fill(document, problem_type)
            if document.project is None and runs:
                self._fill_runs(runs)
        self._tree.blockSignals(False)
        if previous[0]:
            try:
                self.select(*previous)
                return
            except KeyError:
                pass
        self.selectionChanged.emit("", "")

    def _fill(self, document: Document, problem_type: ProblemType | None) -> None:
        scene = document.scene
        if scene is not None:
            for shape in scene.shapes:
                self._add("shape", shape.name, shape_summary(shape))
            for index, region in enumerate(scene.regions):
                self._add(
                    "region",
                    region.name,
                    region_summary(region, problem_type),
                    t.region_colour(index),
                )
            for index, boundary in enumerate(scene.boundaries):
                summary = boundary_summary(boundary, problem_type)
                self._add("boundary", boundary.name, summary, t.boundary_colour(index))
            if DEFAULT_BOUNDARY_NAME in document.boundary_names:
                index = len(scene.boundaries)
                default = Boundary(DEFAULT_BOUNDARY_NAME, Outline(""), scene.default_boundary)
                summary = boundary_summary(default, problem_type)
                self._add("boundary", DEFAULT_BOUNDARY_NAME, summary, t.boundary_colour(index))
        else:
            for index, (name, ids) in enumerate(document.mesh.regions.items()):
                self._add("region", name, f"{len(ids)} triangles", t.region_colour(index))
            for index, (name, ids) in enumerate(document.mesh.boundaries.items()):
                self._add("boundary", name, f"{len(ids)} edges", t.boundary_colour(index))
        if document.project is not None:
            self._fill_runs(document.project.runs())

    def _fill_runs(self, runs) -> None:
        for run in reversed(runs):
            self._add("run", f"run {run.number}", run_summary(run))

    def set_runs(self, runs) -> None:
        """Replace the Runs group, leaving the rest of the tree and the selection alone."""
        selected = self.selected()
        group = self._groups["run"]
        self._tree.blockSignals(True)
        group.takeChildren()
        self._fill_runs(runs)
        self._tree.blockSignals(False)
        if selected[0] == "run":
            try:
                self.select(*selected)
            except KeyError:
                self.selectionChanged.emit("", "")

    def rows(self) -> dict[str, list[tuple[str, str]]]:
        """For each kind, the (name, summary) rows now shown."""
        result = {}
        for kind, group in self._groups.items():
            children = [group.child(i) for i in range(group.childCount())]
            result[kind] = [(c.text(0), c.text(1)) for c in children]
        return result

    def swatches(self, kind: str) -> list[str]:
        """The colour of each row's swatch in a group, as a hex string."""
        group = self._groups[kind]
        size = zoom.px(t.SWATCH)
        colours = []
        for i in range(group.childCount()):
            image = group.child(i).icon(0).pixmap(size, size).toImage()
            colours.append(image.pixelColor(size // 2, size // 2).name())
        return colours

    def select(self, kind: str, name: str) -> None:
        group = self._groups[kind]
        for i in range(group.childCount()):
            if group.child(i).text(0) == name:
                self._tree.setCurrentItem(group.child(i))
                return
        raise KeyError(f"no {kind} named {name!r}")

    def clear_selection(self) -> None:
        self._tree.setCurrentItem(None)
        self._tree.clearSelection()

    def _on_current_changed(self, current: QTreeWidgetItem | None, _previous) -> None:
        if current is None or current.data(0, KIND_ROLE) is None:
            self.selectionChanged.emit("", "")
        else:
            self.selectionChanged.emit(current.data(0, KIND_ROLE), current.data(0, NAME_ROLE))
