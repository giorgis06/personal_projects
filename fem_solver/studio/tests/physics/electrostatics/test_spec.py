import pytest
from examples.capacitor import capacitor_scene
from femstudio.core.scene.boundary import BoundaryCondition
from femstudio.physics import registry


@pytest.fixture
def electrostatics():
    return registry.get("electrostatics")


def test_fields_as_the_plan_lists_them(electrostatics):
    assert [(f.name, f.kind) for f in electrostatics.material_fields] == [("epsilon", "tensor")]
    assert electrostatics.material_fields[0].default == ((1.0, 0.0), (0.0, 1.0))
    kinds = {k.name: [f.name for f in k.fields] for k in electrostatics.boundary_kinds}
    assert kinds == {"dirichlet": ["g"], "neumann": ["g"], "robin": ["g", "kappa"]}
    assert [f.name for f in electrostatics.source_fields] == ["rho"]


def test_output_fields_separate_solved_from_derived(electrostatics):
    outputs = {o.name: o for o in electrostatics.output_fields}
    assert not outputs["u"].derived
    assert all(outputs[n].derived for n in ("E", "E_magnitude", "energy_density"))
    assert outputs["E"].vector and not outputs["E_magnitude"].vector


def test_capacitor_has_no_problem_findings(electrostatics):
    assert electrostatics.validate(capacitor_scene()) == []


def findings_of(electrostatics, scene):
    return {(f.rule, f.subject) for f in electrostatics.validate(scene)}


def test_scene_for_another_problem_type(electrostatics):
    scene = capacitor_scene()
    scene.problem_type = "magnetostatics"
    assert ("problem-type", "scene") in findings_of(electrostatics, scene)


def test_region_missing_a_material_field(electrostatics):
    scene = capacitor_scene()
    scene.regions[0].material = {"mu": 2.0}
    found = findings_of(electrostatics, scene)
    assert ("material-fields", "region 'glass'") in found


def test_material_value_of_the_wrong_type(electrostatics):
    scene = capacitor_scene()
    scene.regions[0].material["epsilon"] = "4"
    assert ("material-fields", "region 'glass'") in findings_of(electrostatics, scene)


def test_unknown_boundary_kind(electrostatics):
    scene = capacitor_scene()
    scene.boundaries[0].condition = BoundaryCondition("periodic", {})
    assert ("boundary-kind", "boundary 'inner_electrode'") in findings_of(electrostatics, scene)


@pytest.mark.parametrize(
    "condition",
    [
        BoundaryCondition("robin", {"g": "0"}),
        BoundaryCondition("dirichlet", {}),
        BoundaryCondition("dirichlet", {"g": "0", "kappa": "1"}),
    ],
)
def test_boundary_fields_must_match_the_kind(electrostatics, condition):
    scene = capacitor_scene()
    scene.boundaries[0].condition = condition
    assert ("boundary-fields", "boundary 'inner_electrode'") in findings_of(electrostatics, scene)


def test_default_boundary_is_checked_like_any_condition(electrostatics):
    scene = capacitor_scene()
    scene.default_boundary = BoundaryCondition("robin", {"g": "0"})
    assert ("boundary-fields", "default boundary") in findings_of(electrostatics, scene)


def test_unknown_source_field(electrostatics):
    scene = capacitor_scene()
    scene.source["sigma"] = "1"
    assert ("source-fields", "source") in findings_of(electrostatics, scene)
