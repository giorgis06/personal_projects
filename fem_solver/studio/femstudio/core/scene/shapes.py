from dataclasses import dataclass

from femstudio.core.scene.operations import Area

Point = tuple[float, float]


@dataclass
class Shape(Area):
    name: str


@dataclass
class Circle(Shape):
    center: Point
    radius: float


@dataclass
class Rectangle(Shape):
    corner: Point  # lower-left
    width: float
    height: float


@dataclass
class Polygon(Shape):
    points: tuple[Point, ...]
