import copy
from dataclasses import dataclass

from femstudio.core.scene.scene import Scene

LIMIT = 100


@dataclass
class _Step:
    label: str
    scene: Scene


class History:
    """Undo and redo by whole-scene snapshots; one step per committed edit."""

    def __init__(self, limit: int = LIMIT) -> None:
        self._limit = limit
        self._undo: list[_Step] = []
        self._redo: list[_Step] = []

    def record(self, scene: Scene, label: str) -> None:
        """Remember `scene` as it is now, before an edit named `label`; drops the redo steps."""
        self._undo.append(_Step(label, copy.deepcopy(scene)))
        del self._undo[: -self._limit]
        self._redo.clear()

    def rollback(self) -> Scene:
        """Forget the step just recorded and return that snapshot, for an edit that was refused."""
        return self._undo.pop().scene

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def undo_label(self) -> str | None:
        return self._undo[-1].label if self._undo else None

    @property
    def redo_label(self) -> str | None:
        return self._redo[-1].label if self._redo else None

    def undo(self, current: Scene) -> Scene:
        step = self._undo.pop()
        self._redo.append(_Step(step.label, copy.deepcopy(current)))
        return step.scene

    def redo(self, current: Scene) -> Scene:
        step = self._redo.pop()
        self._undo.append(_Step(step.label, copy.deepcopy(current)))
        return step.scene

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()
