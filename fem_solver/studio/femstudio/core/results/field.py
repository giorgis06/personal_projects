from dataclasses import dataclass
from typing import Literal

import numpy as np


@dataclass
class Field:
    """Values on a mesh: one per node, or one per triangle. Vectors have shape (n, 2)."""

    name: str
    values: np.ndarray
    unit: str = ""
    location: Literal["node", "triangle"] = "node"

    @property
    def is_vector(self) -> bool:
        return self.values.ndim == 2
