"""Expression language: numbers, + - * / ^, parentheses, x y r theta, pi, one-argument functions.

`^` is right-associative and binds tighter than unary minus, so `-2^2` is -4 and `2^-1` is 0.5.
"""

import math
import re
from dataclasses import dataclass

VARIABLES = ("x", "y", "r", "theta")
CONSTANTS = {"pi": math.pi}
FUNCTIONS = ("sin", "cos", "tan", "exp", "log", "sqrt", "abs")


class ExpressionError(ValueError):
    """The text is not a valid expression in this language."""


@dataclass(frozen=True)
class Number:
    value: float


@dataclass(frozen=True)
class Name:
    name: str


@dataclass(frozen=True)
class Unary:
    op: str
    operand: "Node"


@dataclass(frozen=True)
class Binary:
    op: str
    left: "Node"
    right: "Node"


@dataclass(frozen=True)
class Call:
    function: str
    argument: "Node"


Node = Number | Name | Unary | Binary | Call

_TOKEN = re.compile(
    r"\s*(?:(?P<number>(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
    r"|(?P<name>[A-Za-z_]\w*)"
    r"|(?P<op>[-+*/^()]))"
)


def _tokenize(text: str) -> list[tuple[str, str]]:
    tokens = []
    position = 0
    while text[position:].strip():
        match = _TOKEN.match(text, position)
        if match is None:
            bad = text[position:].lstrip()[0]
            raise ExpressionError(f"unexpected character {bad!r}")
        kind = match.lastgroup
        tokens.append((kind, match.group(kind)))
        position = match.end()
    return tokens


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]]) -> None:
        self.tokens = tokens
        self.index = 0

    def peek(self) -> tuple[str, str] | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def take(self) -> tuple[str, str]:
        token = self.peek()
        if token is None:
            raise ExpressionError("expression ends unexpectedly")
        self.index += 1
        return token

    def accept(self, *ops: str) -> str | None:
        token = self.peek()
        if token is not None and token[0] == "op" and token[1] in ops:
            self.index += 1
            return token[1]
        return None

    def expect(self, op: str) -> None:
        if self.accept(op) is None:
            raise ExpressionError(f"expected {op!r}")

    def parse(self) -> Node:
        node = self.sum()
        if self.peek() is not None:
            raise ExpressionError(f"unexpected {self.peek()[1]!r}")
        return node

    def sum(self) -> Node:
        node = self.product()
        while op := self.accept("+", "-"):
            node = Binary(op, node, self.product())
        return node

    def product(self) -> Node:
        node = self.unary()
        while op := self.accept("*", "/"):
            node = Binary(op, node, self.unary())
        return node

    def unary(self) -> Node:
        if op := self.accept("+", "-"):
            return Unary(op, self.unary())
        return self.power()

    def power(self) -> Node:
        base = self.atom()
        if self.accept("^"):
            return Binary("^", base, self.unary())
        return base

    def atom(self) -> Node:
        kind, text = self.take()
        if kind == "number":
            return Number(float(text))
        if kind == "name":
            return self.name(text)
        if text == "(":
            node = self.sum()
            self.expect(")")
            return node
        raise ExpressionError(f"unexpected {text!r}")

    def name(self, text: str) -> Node:
        calls = self.accept("(")
        if text in FUNCTIONS:
            if not calls:
                raise ExpressionError(f"function {text!r} needs an argument in parentheses")
            argument = self.sum()
            self.expect(")")
            return Call(text, argument)
        if calls:
            raise ExpressionError(f"unknown function {text!r}")
        if text in VARIABLES or text in CONSTANTS:
            return Name(text)
        raise ExpressionError(f"unknown name {text!r}")


def parse(text: str) -> Node:
    """Parse `text` into a tree, or raise ExpressionError."""
    tokens = _tokenize(text)
    if not tokens:
        raise ExpressionError("expression is empty")
    return _Parser(tokens).parse()
