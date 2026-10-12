import json

import pytest
from femstudio.core.scene.boundary import Boundary, BoundaryCondition
from femstudio.core.scene.region import Region
from femstudio.core.scene.scene import Scene
from femstudio.core.scene.serialization import (
    SceneFileError,
    load_scene,
    save_scene,
    scene_from_dict,
    scene_to_dict,
)
from femstudio.core.scene.shapes import Circle, Polygon, Rectangle


def rich_scene() -> Scene:
    disk = Circle("disk", (0.5, -0.5), 1.5)
    slab = Rectangle("slab", (-1.0, -1.0), 2.0, 0.5)
    tri = Polygon("tri", ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)))
    return Scene(
        problem_type="electrostatics",
        shapes=[disk, slab, tri],
        regions=[
            Region("a", (disk | slab) - tri, {"epsilon": ((2.0, 0.5), (0.5, 1.0))}),
            Region("b", disk & slab, {"epsilon": 3.0}),
        ],
        boundaries=[
            Boundary("edge", "disk", BoundaryCondition("robin", {"g": "1", "kappa": "x+2"})),
            Boundary("free", "tri"),
        ],
        source={"rho": "exp(-r^2)"},
    )


def test_round_trip_through_a_file(tmp_path):
    scene = rich_scene()
    save_scene(scene, tmp_path / "scene.json")
    assert load_scene(tmp_path / "scene.json") == scene


def test_round_trip_through_json_text():
    scene = rich_scene()
    assert scene_from_dict(json.loads(json.dumps(scene_to_dict(scene)))) == scene


def test_written_form_matches_a_hand_written_file():
    disk = Circle("disk", (0.0, 0.0), 1.0)
    eps = ((1.0, 0.0), (0.0, 1.0))
    scene = Scene(
        problem_type="electrostatics",
        shapes=[disk],
        regions=[Region("air", disk, {"epsilon": eps})],
        boundaries=[Boundary("rim", "disk", BoundaryCondition("dirichlet", {"g": "0"}))],
        source={"rho": "0"},
    )
    assert scene_to_dict(scene) == {
        "schema_version": 1,
        "problem_type": "electrostatics",
        "shapes": [{"type": "circle", "name": "disk", "center": [0.0, 0.0], "radius": 1.0}],
        "regions": [
            {"name": "air", "area": "disk", "material": {"epsilon": [[1.0, 0.0], [0.0, 1.0]]}}
        ],
        "boundaries": [
            {"name": "rim", "shape": "disk", "condition": {"kind": "dirichlet", "g": "0"}}
        ],
        "source": {"rho": "0"},
    }


def _keys(value):
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key
            yield from _keys(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _keys(inner)


def test_no_tag_numbers_in_a_saved_scene():
    data = scene_to_dict(rich_scene())
    assert not [key for key in _keys(data) if "tag" in key]
    references = [b["shape"] for b in data["boundaries"]]
    assert all(isinstance(ref, str) and not ref.isdigit() for ref in references)


def _good() -> dict:
    return scene_to_dict(rich_scene())


def test_rejects_other_schema_versions():
    data = _good() | {"schema_version": 2}
    with pytest.raises(SceneFileError, match="schema_version"):
        scene_from_dict(data)


def test_rejects_a_missing_key():
    data = _good()
    del data["regions"]
    with pytest.raises(SceneFileError, match="malformed"):
        scene_from_dict(data)


def test_rejects_an_unknown_shape_type():
    data = _good()
    data["shapes"][0]["type"] = "star"
    with pytest.raises(SceneFileError, match="star"):
        scene_from_dict(data)


def test_rejects_a_region_using_an_unknown_shape():
    data = _good()
    data["regions"][1]["area"] = "ghost"
    with pytest.raises(SceneFileError, match="ghost"):
        scene_from_dict(data)


def test_rejects_an_unknown_operation():
    data = _good()
    data["regions"][1]["area"] = {"op": "xor", "operands": ["disk", "slab"]}
    with pytest.raises(SceneFileError, match="xor"):
        scene_from_dict(data)


def test_rejects_text_that_is_not_json(tmp_path):
    path = tmp_path / "scene.json"
    path.write_text("{ not json")
    with pytest.raises(SceneFileError, match="JSON"):
        load_scene(path)
