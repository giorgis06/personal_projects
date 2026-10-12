import pytest
from femstudio.core.expressions.grammar import (
    Binary,
    Call,
    ExpressionError,
    Name,
    Number,
    Unary,
    parse,
)


def test_precedence_builds_the_expected_tree():
    assert parse("1+2*3") == Binary("+", Number(1), Binary("*", Number(2), Number(3)))


def test_power_is_right_associative():
    assert parse("2^3^2") == Binary("^", Number(2), Binary("^", Number(3), Number(2)))


def test_unary_minus_binds_looser_than_power():
    assert parse("-2^2") == Unary("-", Binary("^", Number(2), Number(2)))


def test_function_call_and_names():
    assert parse("sin(theta)") == Call("sin", Name("theta"))
    assert parse("pi") == Name("pi")


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "1 +",
        "* 2",
        "(1",
        "1)",
        "2 3",
        "x y",
        "z",
        "PI",
        "sin",
        "sin()",
        "sin(x, y)",
        "foo(x)",
        "x(2)",
        "pi(2)",
        "x ** 2",
        "1 % 2",
        "1e",
        "x = 1",
        "__import__('os')",
        "$",
    ],
)
def test_rejects_text_outside_the_language(text):
    with pytest.raises(ExpressionError):
        parse(text)
