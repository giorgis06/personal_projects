import math
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

    def outline_points(self, samples: int = 128) -> tuple[Point, ...]:
        """Points of the closed outline, first point repeated at the end."""
        raise NotImplementedError

    @property
    def bounds(self) -> tuple[Point, Point]:
        """Lower-left and upper-right corners of the bounding box."""
        points = self.outline_points()
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        return (min(xs), min(ys)), (max(xs), max(ys))


@dataclass
class Circle(Shape):
    center: Point
    radius: float

    def outline_points(self, samples: int = 128) -> tuple[Point, ...]:
        cx, cy = self.center
        angles = [2 * math.pi * i / samples for i in range(samples + 1)]
        return tuple(
            (cx + self.radius * math.cos(a), cy + self.radius * math.sin(a)) for a in angles
        )


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

    def outline_points(self, samples: int = 128) -> tuple[Point, ...]:
        return (*self.points, self.points[0])


@dataclass
class Polygon(Shape):
    points: tuple[Point, ...]

    @property
    def sides(self) -> tuple[str, ...]:
        """`edge_i` runs from point i to point i + 1, and the last one closes the loop."""
        return tuple(f"edge_{i + 1}" for i in range(len(self.points)))

    def outline_points(self, samples: int = 128) -> tuple[Point, ...]:
        return (*self.points, self.points[0])
