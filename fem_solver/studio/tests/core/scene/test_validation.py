import pytest
from examples.capacitor import capacitor_scene
from femstudio.core.scene.boundary import Boundary, BoundaryCondition
from femstudio.core.scene.region import Region
from femstudio.core.scene.shapes import Circle, Polygon, Rectangle
from femstudio.core.scene.validation import validate


def found(scene):
    return {(f.severity, f.rule, f.subject) for f in validate(scene)}


def rules(scene):
    return {rule for _, rule, _ in found(scene)}


def test_the_capacitor_has_no_findings():
    assert validate(capacitor_scene()) == []


def test_duplicate_shape_names():
    scene = capacitor_scene()
    scene.shapes[1].name = "electrode"
    assert ("error", "names", "shape 'electrode'") in found(scene)


def test_duplicate_region_names():
    scene = capacitor_scene()
    scene.regions[1].name = "glass"
    assert ("error", "names", "region 'glass'") in found(scene)


def test_duplicate_boundary_names():
    scene = capacitor_scene()
    scene.boundaries[1].name = "inner_electrode"
    assert ("error", "names", "boundary 'inner_electrode'") in found(scene)


def test_empty_name():
    scene = capacitor_scene()
    scene.regions[0].name = "  "
    assert ("error", "names", "region #1") in found(scene)


def test_same_name_in_different_groups_is_allowed():
    scene = capacitor_scene()
    scene.boundaries[0].name = "electrode"
    assert "names" not in rules(scene)


@pytest.mark.parametrize(
    "shape",
    [
        Circle("s", (0.0, 0.0), 0.0),
        Circle("s", (0.0, 0.0), -1.0),
        Rectangle("s", (0.0, 0.0), 0.0, 1.0),
        Rectangle("s", (0.0, 0.0), 1.0, -1.0),
        Polygon("s", ((0.0, 0.0), (1.0, 0.0))),
    ],
)
def test_degenerate_shapes(shape):
    scene = capacitor_scene()
    scene.shapes.append(shape)
    assert ("error", "shape-parameters", "shape 's'") in found(scene)


def test_region_using_a_shape_not_in_the_scene():
    scene = capacitor_scene()
    scene.regions.append(Region("x", Circle("loose", (0.0, 0.0), 1.0), {"epsilon": 1.0}))
    assert ("error", "references", "region 'x'") in found(scene)


def test_boundary_on_an_unknown_shape():
    scene = capacitor_scene()
    scene.boundaries.append(Boundary("b", "ghost", BoundaryCondition("dirichlet", {"g": "0"})))
    assert ("error", "references", "boundary 'b'") in found(scene)


def test_bad_expression_in_a_boundary():
    scene = capacitor_scene()
    scene.boundaries[0].condition.values["g"] = "5*cos(phi)"
    assert ("error", "expressions", "boundary 'inner_electrode'") in found(scene)


def test_bad_expression_in_the_source():
    scene = capacitor_scene()
    scene.source["rho"] = "1 +"
    assert ("error", "expressions", "source 'rho'") in found(scene)


def test_good_expressions_pass():
    scene = capacitor_scene()
    scene.boundaries[0].condition.values["g"] = "5*cos(theta)"
    scene.source["rho"] = "exp(-((x-1)^2 + y^2)/0.02)"
    assert "expressions" not in rules(scene)


@pytest.mark.parametrize(
    "tensor",
    [
        ((1.0, 2.0), (0.0, 1.0)),  # not symmetric
        ((1.0, 2.0), (2.0, 1.0)),  # eigenvalues 3 and -1
        ((1.0, 1.0), (1.0, 1.0)),  # eigenvalues 2 and 0
        ((-1.0, 0.0), (0.0, -1.0)),
        ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    ],
)
def test_material_tensor_must_be_symmetric_positive_definite(tensor):
    scene = capacitor_scene()
    scene.regions[0].material["epsilon"] = tensor
    assert ("error", "material-tensor", "region 'glass'") in found(scene)


def test_anisotropic_tensor_with_cross_terms_passes():
    scene = capacitor_scene()
    scene.regions[0].material["epsilon"] = ((2.0, 0.5), (0.5, 1.0))  # eigenvalues (3 +- 2^0.5)/2
    assert "material-tensor" not in rules(scene)


def test_region_without_material():
    scene = capacitor_scene()
    scene.regions[1].material = {}
    assert ("error", "region-material", "region 'air'") in found(scene)


def test_boundary_without_condition_warns():
    scene = capacitor_scene()
    scene.boundaries[1].condition = None
    assert ("warning", "boundary-default", "boundary 'outer_wall'") in found(scene)


def test_no_dirichlet_boundary_warns():
    scene = capacitor_scene()
    for boundary in scene.boundaries:
        boundary.condition = BoundaryCondition("neumann", {"g": "0"})
    assert ("warning", "no-dirichlet", "scene") in found(scene)


def test_one_dirichlet_boundary_is_enough():
    scene = capacitor_scene()
    scene.boundaries[1].condition = BoundaryCondition("neumann", {"g": "0"})
    assert "no-dirichlet" not in rules(scene)
