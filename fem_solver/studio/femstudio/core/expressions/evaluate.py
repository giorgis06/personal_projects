import numpy as np

from femstudio.core.expressions.grammar import (
    CONSTANTS,
    VARIABLES,
    Binary,
    Call,
    Name,
    Node,
    Number,
    Unary,
    parse,
)

_FUNCTIONS = {
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "exp": np.exp,
    "log": np.log,
    "sqrt": np.sqrt,
    "abs": np.abs,
}
_BINARY = {
    "+": np.add,
    "-": np.subtract,
    "*": np.multiply,
    "/": np.divide,
    "^": np.power,
}


def _eval(node: Node, variables: dict[str, np.ndarray]) -> np.ndarray:
    if isinstance(node, Number):
        return np.float64(node.value)
    if isinstance(node, Name):
        return variables[node.name] if node.name in variables else np.float64(CONSTANTS[node.name])
    if isinstance(node, Unary):
        value = _eval(node.operand, variables)
        return -value if node.op == "-" else value
    if isinstance(node, Binary):
        return _BINARY[node.op](_eval(node.left, variables), _eval(node.right, variables))
    return _FUNCTIONS[node.function](_eval(node.argument, variables))


def evaluate(expression: str | Node, x, y) -> np.ndarray:
    """Evaluate at points (x, y); `r` and `theta` are polar coordinates about the origin.

    Domain errors such as log(-1) give nan and division by zero gives inf, never an exception.
    """
    node = parse(expression) if isinstance(expression, str) else expression
    x, y = np.broadcast_arrays(np.asarray(x, dtype=float), np.asarray(y, dtype=float))
    variables = {"x": x, "y": y, "r": np.hypot(x, y), "theta": np.arctan2(y, x)}
    with np.errstate(all="ignore"):
        result = _eval(node, variables)
    return np.broadcast_to(result, x.shape).copy()


def _uses_variables(node: Node) -> bool:
    if isinstance(node, Name):
        return node.name in VARIABLES
    if isinstance(node, Unary):
        return _uses_variables(node.operand)
    if isinstance(node, Binary):
        return _uses_variables(node.left) or _uses_variables(node.right)
    if isinstance(node, Call):
        return _uses_variables(node.argument)
    return False


def constant_value(expression: str | Node) -> float | None:
    """The value of an expression that does not depend on x, y, r or theta; None otherwise."""
    node = parse(expression) if isinstance(expression, str) else expression
    if _uses_variables(node):
        return None
    return float(evaluate(node, 0.0, 0.0))
