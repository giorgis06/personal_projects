from dataclasses import dataclass
from typing import Iterator, Literal


class Area:
    """Anything that covers part of the plane. `|`, `-` and `&` combine areas."""

    def __or__(self, other: "Area") -> "Operation":
        return union(self, other)

    def __sub__(self, other: "Area") -> "Operation":
        return difference(self, other)

    def __and__(self, other: "Area") -> "Operation":
        return intersection(self, other)


@dataclass
class Operation(Area):
    kind: Literal["union", "difference", "intersection"]
    operands: tuple[Area, ...]


def _operation(kind: str, operands: tuple[Area, ...]) -> Operation:
    if len(operands) < 2:
        raise ValueError(f"{kind} needs at least two areas")
    return Operation(kind, operands)


def union(*operands: Area) -> Operation:
    return _operation("union", operands)


def difference(*operands: Area) -> Operation:
    """The first area with every later one removed."""
    return _operation("difference", operands)


def intersection(*operands: Area) -> Operation:
    return _operation("intersection", operands)


def leaves(area: Area) -> Iterator[Area]:
    """The shapes an area is built from, in order."""
    if isinstance(area, Operation):
        for operand in area.operands:
            yield from leaves(operand)
    else:
        yield area
