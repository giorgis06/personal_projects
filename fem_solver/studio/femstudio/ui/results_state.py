import math
from dataclasses import dataclass, replace

from PySide6.QtCore import QObject, Signal

from femstudio.core.project.loaded_run import load_result_set
from femstudio.core.project.run import Run
from femstudio.core.results.reader import ResultError
from femstudio.core.results.result_set import Reading, ResultSet
from femstudio.physics.base import ProblemType
from femstudio.ui.theme import tokens as t

ROUNDING = 1e-12  # of a field's span: an end this close to zero is rounding noise, not a value
WHY_NOT = {
    "created": "it has not been solved",
    "running": "it is still running",
    "failed": "it failed",
}


@dataclass(frozen=True)
class Display:
    """How the field is drawn: which one, the colour range, the colour map, the mesh overlay."""

    field: str = ""
    auto_range: bool = True
    low: float = 0.0
    high: float = 1.0
    colour_map: str = t.DEFAULT_COLOUR_MAP
    mesh_overlay: bool = False


class ResultsState(QObject):
    """The run being looked at and how it is displayed; the views and the panel share it."""

    resultChanged = Signal()  # another run, or none
    displayChanged = Signal()
    probeChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._results: ResultSet | None = None
        self._display = Display()
        self._probe: tuple[float, float] | None = None
        self._message = ""

    # -- what is shown

    @property
    def results(self) -> ResultSet | None:
        return self._results

    @property
    def display(self) -> Display:
        return self._display

    @property
    def message(self) -> str:
        """Why nothing is shown, or an empty string."""
        return self._message

    @property
    def probe(self) -> tuple[float, float] | None:
        return self._probe

    def colour_range(self) -> tuple[float, float]:
        """The range the colours span: the field's own, or the one chosen.

        A map for fields that change sign is centred on zero. A field with one value gets a
        range around it, so the colour bar has something to show.
        """
        results, display = self._results, self._display
        if results is None or display.field not in results.fields:
            return 0.0, 1.0
        if not display.auto_range:
            return display.low, display.high
        low, high = results.value_range(display.field)
        noise = ROUNDING * (high - low)
        low, high = (0.0 if abs(end) < noise else end for end in (low, high))
        if display.colour_map == t.SIGN_CHANGING_MAP and low < 0.0 < high:
            low, high = -max(-low, high), max(-low, high)
        if high == low:
            pad = abs(low) * 0.5 or 1.0
            low, high = low - pad, high + pad
        return low, high

    def reading(self) -> Reading | None:
        """The shown field at the probe, or None when there is no probe or it is outside."""
        if self._results is None or self._probe is None:
            return None
        if self._display.field not in self._results.fields:
            return None
        return self._results.reading(self._display.field, *self._probe)

    # -- changing it

    def show_run(self, run: Run, problem_type: ProblemType) -> bool:
        """Load a run's result. On failure nothing is shown and `message` says why."""
        if run.state != "success":
            reason = WHY_NOT.get(run.state, f"its state is {run.state}")
            self._fail(f"run {run.number} has no result: {reason}")
            return False
        try:
            results = load_result_set(run, problem_type)
        except (ResultError, OSError, ValueError, KeyError) as error:
            self._fail(f"run {run.number} cannot be read: {error}")
            return False
        previous = self._display.field
        self._results = results
        self._message = ""
        field = previous if previous in results.fields else results.names()[0]
        self._display = replace(self._display, field=field, auto_range=True)
        self._probe = self._probe if self._reading_exists() else None
        self.resultChanged.emit()
        return True

    def clear(self, message: str = "") -> None:
        had = self._results is not None or self._message != message
        self._results = None
        self._message = message
        self._probe = None
        self._display = replace(self._display, field="", auto_range=True)
        if had:
            self.resultChanged.emit()

    def _fail(self, message: str) -> None:
        self.clear(message)

    def _reading_exists(self) -> bool:
        results = self._results
        if results is None or self._probe is None:
            return False
        return results.reading(self._display.field, *self._probe) is not None

    def set_field(self, name: str) -> None:
        if self._results is None or name not in self._results.fields:
            raise KeyError(name)
        if name != self._display.field:
            self._display = replace(self._display, field=name, auto_range=True)
            self.displayChanged.emit()
            self.probeChanged.emit()

    def set_range(self, low: float, high: float) -> None:
        if not (math.isfinite(low) and math.isfinite(high)):
            raise ValueError("the range must be finite numbers")
        if low >= high:
            raise ValueError("the range must run from a smaller to a larger number")
        self._display = replace(self._display, auto_range=False, low=low, high=high)
        self.displayChanged.emit()

    def use_automatic_range(self) -> None:
        if not self._display.auto_range:
            self._display = replace(self._display, auto_range=True)
            self.displayChanged.emit()

    def set_colour_map(self, name: str) -> None:
        if name not in t.COLOUR_MAPS:
            raise KeyError(name)
        if name != self._display.colour_map:
            self._display = replace(self._display, colour_map=name)
            self.displayChanged.emit()

    def set_mesh_overlay(self, on: bool) -> None:
        if on != self._display.mesh_overlay:
            self._display = replace(self._display, mesh_overlay=on)
            self.displayChanged.emit()

    def set_probe(self, x: float, y: float) -> None:
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError("the probe position must be finite numbers")
        self._probe = (x, y)
        self.probeChanged.emit()

    def clear_probe(self) -> None:
        if self._probe is not None:
            self._probe = None
            self.probeChanged.emit()
