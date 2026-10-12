import pytest
from femstudio.core.scene.boundary import Boundary
from femstudio.core.scene.region import Region
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.shapes import Circle


def test_lookup_by_name():
    disk = Circle("disk", (0.0, 0.0), 1.0)
    region = Region("air", disk, {"epsilon": 1.0})
    boundary = Boundary("rim", "disk")
    scene = Scene("electrostatics", [disk], [region], [boundary])
    assert scene.shape("disk") is disk
    assert scene.region("air") is region
    assert scene.boundary("rim") is boundary


def test_lookup_of_a_missing_name_raises():
    with pytest.raises(KeyError, match="no region named 'glass'"):
        Scene("electrostatics").region("glass")
