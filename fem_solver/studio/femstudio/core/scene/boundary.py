from dataclasses import dataclass, field


@dataclass
class BoundaryCondition:
    """`kind` and the keys of `values` come from the problem type; each value is an expression."""

    kind: str
    values: dict[str, str] = field(default_factory=dict)


@dataclass
class Boundary:
    """The outline of the shape called `shape`. Without a condition it is insulating."""

    name: str
    shape: str
    condition: BoundaryCondition | None = None
