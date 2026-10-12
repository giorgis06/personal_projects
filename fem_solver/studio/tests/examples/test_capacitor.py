from pathlib import Path

from examples.capacitor import capacitor_scene
from femstudio.core.scene.operations import leaves
from femstudio.core.scene.serialization import load_scene

SCENE_FILE = Path(__file__).resolve().parents[2] / "examples" / "capacitor.scene.json"


def test_json_file_matches_the_code():
    assert load_scene(SCENE_FILE) == capacitor_scene()


def test_geometry_is_the_reference_capacitor():
    scene = capacitor_scene()
    radii = {shape.name: shape.radius for shape in scene.shapes}
    assert radii == {"electrode": 0.2, "glass_outer": 0.5, "wall": 2.0}
    assert [region.name for region in scene.regions] == ["glass", "air"]
    assert [boundary.name for boundary in scene.boundaries] == ["inner_electrode", "outer_wall"]


def test_materials():
    scene = capacitor_scene()
    assert scene.region("glass").material["epsilon"] == ((4.0, 0.0), (0.0, 4.0))
    assert scene.region("air").material["epsilon"] == ((1.0, 0.0), (0.0, 1.0))


def test_regions_are_rings_between_the_named_circles():
    scene = capacitor_scene()
    assert [leaf.name for leaf in leaves(scene.region("glass").area)] == [
        "glass_outer",
        "electrode",
    ]
    assert [leaf.name for leaf in leaves(scene.region("air").area)] == ["wall", "glass_outer"]
