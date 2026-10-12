import copy

import pytest
from examples.capacitor import capacitor_scene
from femstudio.core.scene import physics_editing as edit
from femstudio.core.scene.boundary import BoundaryCondition
from femstudio.core.scene.editing import EditError
from femstudio.core.scene.validation import validate


@pytest.fixture
def scene():
    return capacitor_scene()


def test_a_material_is_replaced_by_a_number_or_a_matrix(scene):
    edit.set_material(scene, "glass", {"epsilon": 6})
    assert scene.region("glass").material == {"epsilon": 6.0}
    edit.set_material(scene, "glass", {"epsilon": [[4, 1], [1, 2]]})
    assert scene.region("glass").material == {"epsilon": ((4.0, 1.0), (1.0, 2.0))}


@pytest.mark.parametrize(
    "value", ["x", float("nan"), float("inf"), [[1, 2]], [[1, 2, 3], [4, 5, 6]], [1, 2], None]
)
def test_a_material_that_is_not_a_number_or_matrix_is_refused_and_changes_nothing(scene, value):
    before = copy.deepcopy(scene)
    with pytest.raises(EditError):
        edit.set_material(scene, "glass", {"epsilon": value})
    assert scene == before


def test_unknown_names_are_refused(scene):
    with pytest.raises(EditError, match="no region named 'nope'"):
        edit.set_material(scene, "nope", {})
    with pytest.raises(EditError, match="no boundary named 'nope'"):
        edit.set_condition(scene, "nope", None)


def test_a_condition_is_set_and_cleared(scene):
    edit.set_condition(scene, "inner_electrode", BoundaryCondition("robin", {"kappa": "2"}))
    assert scene.boundary("inner_electrode").condition == BoundaryCondition("robin", {"kappa": "2"})
    edit.set_condition(scene, "inner_electrode", None)
    assert scene.boundary("inner_electrode").condition is None


def test_condition_values_must_be_expression_text(scene):
    with pytest.raises(EditError, match="expressions"):
        edit.set_condition(scene, "inner_electrode", BoundaryCondition("dirichlet", {"g": 5}))


def test_the_condition_is_copied_so_the_caller_cannot_change_it_later(scene):
    values = {"g": "1"}
    edit.set_default_condition(scene, BoundaryCondition("dirichlet", values))
    values["g"] = "2"
    assert scene.default_boundary.values == {"g": "1"}


def test_default_condition_and_source(scene):
    edit.set_default_condition(scene, BoundaryCondition("dirichlet", {"g": "0"}))
    assert scene.default_boundary == BoundaryCondition("dirichlet", {"g": "0"})
    edit.set_default_condition(scene, None)
    assert scene.default_boundary is None
    edit.set_source(scene, {"rho": "x"})
    assert scene.source == {"rho": "x"}
    with pytest.raises(EditError):
        edit.set_source(scene, {"rho": 1})


def test_an_expression_that_does_not_parse_is_kept_and_validation_reports_it(scene):
    edit.set_condition(scene, "inner_electrode", BoundaryCondition("dirichlet", {"g": "5 *"}))
    findings = [f for f in validate(scene) if f.rule == "expressions"]
    assert [f.subject for f in findings] == ["boundary 'inner_electrode'"]
