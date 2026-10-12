import pytest
from femstudio.core.scene.boundary import BoundaryCondition
from femstudio.physics import registry
from femstudio.ui.widgets.condition_edit import ConditionEdit
from femstudio.ui.widgets.expression_edit import ExpressionEdit
from femstudio.ui.widgets.field_form import FieldForm
from femstudio.ui.widgets.number_edit import NumberEdit
from femstudio.ui.widgets.tensor_edit import TensorEdit

pytestmark = pytest.mark.ui


@pytest.fixture
def problem():
    return registry.get("electrostatics")


def test_an_expression_that_parses_is_valid(qtbot):
    edit = ExpressionEdit("5*cos(theta)")
    qtbot.addWidget(edit)
    assert edit.is_valid()
    assert edit.property("state") == ""


def test_an_expression_that_does_not_parse_marks_itself_and_says_why(qtbot):
    edit = ExpressionEdit("5 *")
    qtbot.addWidget(edit)
    assert not edit.is_valid()
    assert edit.property("state") == "invalid"
    assert edit.toolTip() == edit.error() != ""
    edit.setText("5 * x")
    assert edit.is_valid()
    assert edit.property("state") == ""
    assert edit.toolTip() == ""


def test_an_unknown_name_is_reported(qtbot):
    edit = ExpressionEdit("z + 1")
    qtbot.addWidget(edit)
    assert "unknown name 'z'" in edit.error()


@pytest.mark.parametrize("text", ["4,5", "4.5.", "", "-", "1,000.5", "1e", "abc", "nan"])
def test_a_number_edit_does_not_guess_at_text_that_is_not_a_number(qtbot, text):
    edit = NumberEdit(4.5)
    qtbot.addWidget(edit)
    edit.setText(text)
    assert not edit.is_valid()
    assert edit.error() == edit.toolTip() == "not a number"
    assert edit.property("state") == "invalid"
    with pytest.raises(ValueError):
        edit.value()
    edit.setText("4.5")
    assert edit.value() == 4.5
    assert edit.property("state") == ""


def test_a_number_edit_reads_the_same_way_in_any_locale(qtbot):
    from PySide6.QtCore import QLocale
    from PySide6.QtGui import QValidator

    previous = QLocale()
    QLocale.setDefault(QLocale("de_DE"))
    try:
        edit = NumberEdit(1.0)
        qtbot.addWidget(edit)
        accepted = QValidator.State.Acceptable
        assert edit.validator().validate("8.85e-12", 0)[0] == accepted
        assert edit.validator().validate("4,5", 0)[0] != accepted
    finally:
        QLocale.setDefault(previous)


def test_a_tensor_edit_with_an_unreadable_entry_says_so(qtbot):
    edit = TensorEdit(((4.0, 0.0), (0.0, 2.0)))
    qtbot.addWidget(edit)
    assert edit.error() == ""
    edit.box(0, 1).setText("1,5")
    assert edit.error() == "not a number"
    with pytest.raises(ValueError):
        edit.value()


def test_a_field_form_lists_numbers_that_cannot_be_read(qtbot, problem):
    form = FieldForm(problem.material_fields, {"epsilon": 4.0})
    qtbot.addWidget(form)
    assert form.unreadable() == []
    form.editor("epsilon").box(1, 1).setText("")
    (reason,) = form.unreadable()
    assert reason == "Permittivity [1]: not a number" or reason.endswith(": not a number")


def test_a_tensor_edit_keeps_a_scalar_a_scalar(qtbot):
    edit = TensorEdit(4.0)
    qtbot.addWidget(edit)
    assert edit.value() == 4.0
    edit.set_value(((4.0, 0.0), (0.0, 4.0)))
    assert edit.value() == 4.0


def test_a_tensor_edit_is_symmetric(qtbot):
    edit = TensorEdit(((4.0, 0.0), (0.0, 2.0)))
    qtbot.addWidget(edit)
    assert edit.value() == ((4.0, 0.0), (0.0, 2.0))
    edit.box(0, 1).set_value(1.5)
    assert edit.box(1, 0).value() == 1.5
    assert not edit.box(1, 0).isEnabled()
    assert edit.value() == ((4.0, 1.5), (1.5, 2.0))


def test_a_field_form_gives_back_what_the_scene_stores(qtbot, problem):
    form = FieldForm(problem.material_fields + problem.source_fields, {"epsilon": 4.0, "rho": "x"})
    qtbot.addWidget(form)
    assert form.values() == {"epsilon": 4.0, "rho": "x"}
    assert form.problems() == []


def test_a_field_form_fills_missing_values_with_the_fields_defaults(qtbot, problem):
    form = FieldForm(problem.material_fields + problem.source_fields, {})
    qtbot.addWidget(form)
    assert form.values() == {"epsilon": 1.0, "rho": "0"}


def test_a_field_form_lists_expressions_that_do_not_parse(qtbot, problem):
    form = FieldForm(problem.source_fields, {"rho": "1 +"})
    qtbot.addWidget(form)
    (problem_text,) = form.problems()
    assert problem_text.startswith("Charge density [C/m^3]:")


def test_a_condition_edit_offers_the_problems_kinds(qtbot, problem):
    edit = ConditionEdit(problem.boundary_kinds, None, "none")
    qtbot.addWidget(edit)
    combo = edit.findChild(type(edit._combo), "kind")
    assert [combo.itemText(i) for i in range(combo.count())] == [
        "none",
        *[k.label for k in problem.boundary_kinds],
    ]
    assert edit.kind_name() is None
    assert edit.condition() is None


def test_a_condition_edit_shows_only_the_chosen_kinds_fields(qtbot, problem):
    condition = BoundaryCondition("robin", {"kappa": "2", "u_ref": "5"})
    edit = ConditionEdit(problem.boundary_kinds, condition, "none")
    qtbot.addWidget(edit)
    edit.show()
    shown = [k.name for k in problem.boundary_kinds if edit.form(k.name).isVisible()]
    assert shown == ["robin"]
    assert edit.condition() == condition
    edit.set_kind(problem.boundary_kinds[0].name)
    assert edit.condition() == BoundaryCondition(problem.boundary_kinds[0].name, {"g": "0"})
    edit.set_kind(None)
    assert edit.condition() is None
    assert edit.problems() == []


def test_a_condition_edit_reports_the_chosen_kinds_bad_expressions(qtbot, problem):
    condition = BoundaryCondition("dirichlet", {"g": "5 *"})
    edit = ConditionEdit(problem.boundary_kinds, condition, "none")
    qtbot.addWidget(edit)
    assert len(edit.problems()) == 1
