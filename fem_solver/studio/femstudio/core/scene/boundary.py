from dataclasses import dataclass, field


@dataclass
class BoundaryCondition:
    """`kind` and the keys of `values` come from the problem type; each value is an expression."""

    kind: str
    values: dict[str, str] = field(default_factory=dict)


@dataclass
class Outline:
    """The whole outline of a shape."""

    shape: str


@dataclass
class Side:
    """One side of a shape, by the name listed in the shape's `sides`."""

    shape: str
    side: str


@dataclass
class Between:
    """The curve two regions share. It is interior; without a condition it is simply continuous."""

    first: str
    second: str


Curve = Outline | Side | Between


@dataclass
class Boundary:
    """A named curve. Without a condition it is insulating (neumann, g = 0)."""

    name: str
    curve: Curve
    condition: BoundaryCondition | None = None
