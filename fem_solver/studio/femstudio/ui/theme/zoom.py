"""The interface scale factor. Tokens stay the 100 % values; sized things go through `px`/`pt`."""

from PySide6.QtCore import QSettings

MINIMUM = 0.7
MAXIMUM = 2.0
STEP = 0.1
SETTINGS_KEY = "interface/zoom"

_current = 1.0


def clamp(factor: float) -> float:
    """The nearest allowed factor, in steps of 0.1."""
    return round(min(max(factor, MINIMUM), MAXIMUM), 1)


def zoomed_in(factor: float) -> float:
    return clamp(factor + STEP)


def zoomed_out(factor: float) -> float:
    return clamp(factor - STEP)


def current() -> float:
    return _current


def set_current(factor: float) -> float:
    global _current
    _current = clamp(factor)
    return _current


def px(value: float, factor: float | None = None) -> int:
    """A token's pixel size at the given (or current) zoom; a non-zero size never drops below 1."""
    factor = _current if factor is None else factor
    if value == 0:
        return 0
    return max(1, round(value * factor))


def pt(value: float, factor: float | None = None) -> float:
    """A token's point size at the given (or current) zoom."""
    factor = _current if factor is None else factor
    return round(value * factor, 1)


def percent(factor: float | None = None) -> str:
    factor = _current if factor is None else factor
    return f"{round(factor * 100)} %"


def load(settings: QSettings) -> float:
    try:
        return clamp(float(settings.value(SETTINGS_KEY, 1.0)))
    except (TypeError, ValueError):
        return 1.0


def save(settings: QSettings, factor: float) -> None:
    settings.setValue(SETTINGS_KEY, clamp(factor))
