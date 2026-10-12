from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from femstudio.core.project.document import Document
from femstudio.ui.results_state import ResultsState
from femstudio.ui.theme import tokens as t
from femstudio.ui.theme import zoom
from femstudio.ui.widgets.number_edit import NumberEdit
from femstudio.ui.widgets.readouts import PairsGrid, Section, label

NO_RESULT = "No result yet."
PROBE_HINT = "Double-click the view, or type a position."
OUTSIDE = "Outside the mesh."
MIN_CONTENTS = 12  # characters; the dock is narrow, so a long field label is cut, not widened


def _with_unit(value: float, unit: str) -> str:
    return f"{value:.5g} {unit}".strip()


class ResultsPanel(QWidget):
    """What the field views show: the run, the Display group and the Probe readout."""

    def __init__(self, results: ResultsState) -> None:
        super().__init__()
        self._state = results
        self._kind, self._name = "", ""
        self._widgets: dict[str, QWidget] = {}
        self._grids: dict[str, PairsGrid] = {}
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._note = label(NO_RESULT, "note")
        self._note.setWordWrap(True)
        self._layout.addWidget(self._note)
        self._body = QWidget()
        self._layout.addWidget(self._body)
        self._layout.addStretch(1)
        results.resultChanged.connect(self._rebuild)
        results.displayChanged.connect(self._sync)
        results.probeChanged.connect(self._sync_probe)
        self._rebuild()

    # -- what the tests and the window read

    def text(self) -> str:
        return self._note.text()

    def widget(self, key: str) -> QWidget:
        return self._widgets[key]

    def run_rows(self) -> list[tuple[str, str]]:
        return self._grids["run"].rows if self._widgets else []

    def probe_rows(self) -> list[tuple[str, str]]:
        return self._grids["probe"].rows if self._widgets else []

    # -- showing the result

    def update_view(self, document: Document | None, kind: str, name: str) -> None:
        self._kind, self._name = kind, name
        self._set_note()

    def _set_note(self) -> None:
        if self._state.results is not None:
            self._note.setText("")
            self._note.hide()
            return
        text = self._state.message
        if not text:
            text = f"{self._name}: no result loaded." if self._kind == "run" else NO_RESULT
        self._note.setText(text)
        self._note.show()

    def _rebuild(self) -> None:
        self._body.hide()
        self._body.deleteLater()
        self._body = QWidget()
        self._layout.insertWidget(self._layout.count() - 1, self._body)
        self._widgets, self._grids = {}, {}
        self._set_note()
        results = self._state.results
        if results is None:
            return
        body = QVBoxLayout(self._body)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(zoom.px(t.SECTION_GAP))
        run = PairsGrid()
        self._grids["run"] = run
        body.addWidget(Section("Run", run))
        body.addWidget(Section("Display", self._display_form(results)))
        body.addWidget(Section("Probe", self._probe_form()))
        self._sync()
        self._sync_probe()

    @staticmethod
    def _stacked(layout: QVBoxLayout, title: str, widget: QWidget) -> None:
        layout.addWidget(label(title, "key"))
        layout.addWidget(widget)

    def _combo(self, key: str, items: list[tuple[str, str]], changed) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName(key)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(MIN_CONTENTS)
        for text, data in items:
            combo.addItem(text, data)
        combo.activated.connect(lambda _index: changed(combo.currentData()))
        self._widgets[key] = combo
        return combo

    def _display_form(self, results) -> QWidget:
        holder = QWidget()
        form = QVBoxLayout(holder)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(zoom.px(t.GAP))
        fields = [
            (f"{results.label(n)} [{results.unit(n)}]" if results.unit(n) else results.label(n), n)
            for n in results.names()
        ]
        self._stacked(form, "Field", self._combo("field", fields, self._state.set_field))
        colours = [(name, name) for name in t.COLOUR_MAPS]
        self._stacked(form, "Colours", self._combo("colours", colours, self._set_colours))
        auto = QCheckBox("Automatic range")
        auto.setObjectName("auto_range")
        auto.toggled.connect(self._range_mode)
        self._widgets["auto_range"] = auto
        form.addWidget(auto)
        low, high = NumberEdit(0.0), NumberEdit(1.0)
        low.setObjectName("low")
        high.setObjectName("high")
        self._widgets["low"], self._widgets["high"] = low, high
        ends = QWidget()
        ends_layout = QHBoxLayout(ends)
        ends_layout.setContentsMargins(0, 0, 0, 0)
        ends_layout.addWidget(low)
        ends_layout.addWidget(high)
        self._stacked(form, "Range, from and to", ends)
        apply = QPushButton("Apply range")
        apply.setObjectName("apply_range")
        apply.clicked.connect(self.apply_range)
        self._widgets["apply_range"] = apply
        row = QHBoxLayout()
        row.addWidget(apply)
        row.addStretch(1)
        form.addLayout(row)
        message = label("", "note")
        message.setWordWrap(True)
        self._widgets["range_message"] = message
        form.addWidget(message)
        overlay = QCheckBox("Mesh overlay")
        overlay.setObjectName("overlay")
        overlay.toggled.connect(self._state.set_mesh_overlay)
        self._widgets["overlay"] = overlay
        form.addWidget(overlay)
        return holder

    def _probe_form(self) -> QWidget:
        holder = QWidget()
        form = QVBoxLayout(holder)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(zoom.px(t.GAP))
        x, y = NumberEdit(0.0), NumberEdit(0.0)
        x.setObjectName("probe_x")
        y.setObjectName("probe_y")
        self._widgets["probe_x"], self._widgets["probe_y"] = x, y
        self._stacked(form, "x [m]", x)
        self._stacked(form, "y [m]", y)
        place = QPushButton("Probe")
        place.setObjectName("place_probe")
        place.clicked.connect(self.place_probe)
        self._widgets["place_probe"] = place
        row = QHBoxLayout()
        row.addWidget(place)
        row.addStretch(1)
        form.addLayout(row)
        grid = PairsGrid()
        self._grids["probe"] = grid
        form.addWidget(grid)
        return holder

    # -- committing what the user typed

    def _set_colours(self, name: str) -> None:
        self._state.set_colour_map(name)

    def _range_mode(self, automatic: bool) -> None:
        if automatic:
            self._state.use_automatic_range()
        else:
            low, high = self._state.colour_range()
            self._widgets["low"].set_value(low)
            self._widgets["high"].set_value(high)
            self.apply_range()

    def apply_range(self) -> None:
        """Use the typed range; an unreadable or reversed one is refused with the reason."""
        message = self._widgets["range_message"]
        low, high = self._widgets["low"], self._widgets["high"]
        try:
            self._state.set_range(low.value(), high.value())
        except ValueError as error:
            message.setText(str(error))
            self._sync()
            return
        message.setText("")

    def place_probe(self) -> None:
        x, y = self._widgets["probe_x"], self._widgets["probe_y"]
        try:
            self._state.set_probe(x.value(), y.value())
        except ValueError as error:
            self._grids["probe"].set_rows([("", str(error))])

    # -- following the state

    def _sync(self) -> None:
        results, display = self._state.results, self._state.display
        if results is None or "field" not in self._widgets:
            return
        field, colours = self._widgets["field"], self._widgets["colours"]
        auto, overlay = self._widgets["auto_range"], self._widgets["overlay"]
        for widget in (field, colours, auto, overlay):
            widget.blockSignals(True)
        field.setCurrentIndex(max(field.findData(display.field), 0))
        colours.setCurrentIndex(max(colours.findData(display.colour_map), 0))
        auto.setChecked(display.auto_range)
        overlay.setChecked(display.mesh_overlay)
        for widget in (field, colours, auto, overlay):
            widget.blockSignals(False)
        low, high = self._state.colour_range()
        self._widgets["low"].set_value(low)
        self._widgets["high"].set_value(high)
        manual = not display.auto_range
        self._widgets["low"].setEnabled(manual)
        self._widgets["high"].setEnabled(manual)
        self._widgets["apply_range"].setEnabled(manual)
        unit = results.unit(display.field)
        self._grids["run"].set_rows(
            [
                ("run", str(results.run_number)),
                ("nodes", str(results.mesh.n_nodes)),
                ("triangles", str(results.mesh.n_triangles)),
                ("range", f"{_with_unit(low, unit)} to {_with_unit(high, unit)}"),
            ]
        )
        self._sync_probe()

    def _sync_probe(self) -> None:
        results, display = self._state.results, self._state.display
        if results is None or "probe_x" not in self._widgets:
            return
        probe = self._state.probe
        grid = self._grids["probe"]
        if probe is None:
            grid.set_rows([("", PROBE_HINT)])
            return
        for key, value in zip(("probe_x", "probe_y"), probe, strict=True):
            self._widgets[key].set_value(value)
        reading = self._state.reading()
        if reading is None:
            grid.set_rows([("", OUTSIDE)])
            return
        unit = results.unit(display.field)
        rows = [
            ("x, y", f"{probe[0]:.4g}, {probe[1]:.4g}"),
            (display.field, _with_unit(reading.value, unit)),
            ("triangle", str(reading.triangle)),
        ]
        if reading.components is not None:
            ex, ey = reading.components
            rows.insert(2, ("components", f"{ex:.4g}, {ey:.4g}"))
        grid.set_rows(rows)
