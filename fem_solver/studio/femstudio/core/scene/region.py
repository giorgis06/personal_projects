from dataclasses import dataclass, field

from femstudio.core.scene.operations import Area

Matrix = tuple[tuple[float, float], tuple[float, float]]
MaterialValue = float | Matrix


@dataclass
class Region:
    """A named area. `material` maps field names to values; the problem type defines the fields."""

    name: str
    area: Area
    material: dict[str, MaterialValue] = field(default_factory=dict)
