from dataclasses import dataclass

from femstudio.core.scene.operations import Area

Point = tuple[float, float]


@dataclass
class Shape(Area):
    name: str

    @property
    def sides(self) -> tuple[str, ...]:
        """Names of the sides a boundary can pick; a circle has only its outline."""
        return ()


@dataclass
class Circle(Shape):
    center: Point
    radius: float


@dataclass
class Rectangle(Shape):
    corner: Point  # lower-left
    width: float
    height: float

    @property
    def points(self) -> tuple[Point, ...]:
        """Corners counter-clockwise from `corner`; side i runs from point i to point i + 1."""
        x, y = self.corner
        return (
            (x, y),
            (x + self.width, y),
            (x + self.width, y + self.height),
            (x, y + self.height),
        )

    @property
    def sides(self) -> tuple[str, ...]:
        return ("bottom", "right", "top", "left")


@dataclass
class Polygon(Shape):
    points: tuple[Point, ...]

    @property
    def sides(self) -> tuple[str, ...]:
        """`edge_i` runs from point i to point i + 1, and the last one closes the loop."""
        return tuple(f"edge_{i + 1}" for i in range(len(self.points)))
