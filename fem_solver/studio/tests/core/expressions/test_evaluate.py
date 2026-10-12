import math

import numpy as np
import pytest
from femstudio.core.expressions.evaluate import constant_value, evaluate
from femstudio.core.expressions.grammar import ExpressionError


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2*3+4", 10.0),
        ("2*(3+4)", 14.0),
        ("10-4-3", 3.0),
        ("8/4/2", 1.0),
        ("-2^2", -4.0),
        ("2^3^2", 512.0),
        ("2^-1", 0.5),
        ("+3", 3.0),
        ("1e-3", 0.001),
        (".5", 0.5),
        ("pi", math.pi),
        ("sqrt(16)", 4.0),
        ("abs(-3)", 3.0),
        ("log(exp(2))", 2.0),
        ("sin(pi/2)", 1.0),
        ("tan(0)", 0.0),
    ],
)
def test_constant_expressions(text, expected):
    assert evaluate(text, 0.0, 0.0) == pytest.approx(expected)


def test_polar_variables():
    assert evaluate("r", 3.0, 4.0) == pytest.approx(5.0)
    assert evaluate("theta", -1.0, 0.0) == pytest.approx(math.pi)
    assert evaluate("theta", 0.0, 1.0) == pytest.approx(math.pi / 2)


def test_contract_example_source():
    # exp(-0.01 / 0.02) = exp(-0.5), worked out by hand
    value = evaluate("exp(-((x-1)^2 + y^2)/0.02)", 1.1, 0.0)
    assert value == pytest.approx(0.6065306597)


def test_boundary_function_of_angle():
    assert evaluate("5*cos(theta)", 2.0, 0.0) == pytest.approx(5.0)
    assert evaluate("5*cos(theta)", 0.0, 3.0) == pytest.approx(0.0, abs=1e-12)


def test_evaluates_on_arrays():
    x = np.array([0.0, 1.0, 2.0])
    np.testing.assert_allclose(evaluate("x^2", x, 0.0), [0.0, 1.0, 4.0])


def test_constant_is_broadcast_to_the_shape_of_the_points():
    result = evaluate("5", np.zeros((2, 3)), np.zeros((2, 3)))
    np.testing.assert_array_equal(result, np.full((2, 3), 5.0))


def test_domain_errors_give_nan_and_inf_not_exceptions():
    assert np.isnan(evaluate("log(-1)", 0.0, 0.0))
    assert np.isinf(evaluate("1/0", 0.0, 0.0))


def test_invalid_text_raises():
    with pytest.raises(ExpressionError):
        evaluate("x +", 0.0, 0.0)


@pytest.mark.parametrize(("text", "expected"), [("5", 5.0), ("2*pi", 2 * math.pi), ("1 - 1", 0.0)])
def test_constant_value_of_a_constant(text, expected):
    assert constant_value(text) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["x", "1 + y", "sin(theta)", "exp(-r)"])
def test_constant_value_is_none_when_position_matters(text):
    assert constant_value(text) is None


def test_constant_value_of_invalid_text_raises():
    with pytest.raises(ExpressionError):
        constant_value("2 +")
