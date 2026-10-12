import ast
import re
from pathlib import Path

from matplotlib.colors import CSS4_COLORS

UI = Path(__file__).resolve().parents[2] / "femstudio" / "ui"
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
FUNCTION = re.compile(r"\brgba?\(")
PIXELS = re.compile(r"\b\d+(\.\d+)?px\b")
FONT_FAMILIES = {"IBM Plex Sans", "IBM Plex Mono"}
SIZE_METHODS = {
    "setContentsMargins",
    "setSpacing",
    "setHorizontalSpacing",
    "setVerticalSpacing",
    "addSpacing",
    "resize",
    "setFixedSize",
    "setFixedWidth",
    "setFixedHeight",
    "setMinimumWidth",
    "setMinimumHeight",
    "setPointSize",
}


def modules_outside_theme() -> list[Path]:
    return [p for p in UI.rglob("*.py") if "theme" not in p.relative_to(UI).parts]


def literals_in(source: str) -> list[str]:
    """Colours, font names and pixel sizes spelled out in a module's code."""
    tree = ast.parse(source)
    in_format_spec = {
        id(inner)
        for node in ast.walk(tree)
        if isinstance(node, ast.FormattedValue) and node.format_spec is not None
        for inner in ast.walk(node.format_spec)
    }
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in in_format_spec:
                continue
            text = node.value
            if HEX.search(text) or FUNCTION.search(text) or PIXELS.search(text):
                found.append(text)
            elif text.lower() in CSS4_COLORS or text in FONT_FAMILIES:
                found.append(text)
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") in SIZE_METHODS:
            for argument in node.args:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, (int, float)):
                    if argument.value not in (0, 1):
                        found.append(f"{node.func.attr}({argument.value})")
    return found


def test_scanner_finds_each_kind_of_literal():
    source = (
        'a = "#1d5fb8"\nb = "rgba(0, 0, 0, .5)"\nc = "12px"\nd = "steelblue"\n'
        'e = "IBM Plex Sans"\nf = widget.setContentsMargins(4, 0, 0, 0)\n'
    )
    found = literals_in(source)
    assert len(found) == 6, found


def test_scanner_leaves_ordinary_text_and_zero_margins_alone():
    source = 'a = "Scene"\nb = f"{v:g}"\nc = widget.setContentsMargins(0, 0, 0, 0)\nd = "#"\n'
    assert literals_in(source) == []


def test_no_colour_font_or_pixel_literal_outside_the_theme():
    offenders = {
        str(p.relative_to(UI)): found
        for p in modules_outside_theme()
        if (found := literals_in(p.read_text()))
    }
    assert offenders == {}
