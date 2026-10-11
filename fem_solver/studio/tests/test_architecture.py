import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "femstudio"
FORBIDDEN = {"PySide6", "PyQt5", "PyQt6", "shiboken6", "qtpy", "pyvista", "pyvistaqt", "vtk"}


def forbidden_imports(source: str) -> list[str]:
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names = [node.module or ""]
        else:
            continue
        found += [name for name in names if name.split(".")[0] in FORBIDDEN]
    return found


def modules_outside_ui() -> list[Path]:
    return [p for p in PACKAGE.rglob("*.py") if "ui" not in p.relative_to(PACKAGE).parts]


def test_scanner_flags_each_import_form():
    source = "import PySide6.QtCore\nfrom pyvista import Plotter\nimport numpy\nfrom . import x\n"
    assert forbidden_imports(source) == ["PySide6.QtCore", "pyvista"]


def test_scanner_ignores_unrelated_imports():
    assert forbidden_imports("import numpy as np\nfrom femstudio.ui import main_window\n") == []


def test_scan_covers_the_logic_packages():
    scanned = {p.relative_to(PACKAGE).parts[0] for p in modules_outside_ui()}
    assert {"core", "physics", "backends"} <= scanned


def test_no_qt_or_pyvista_outside_ui():
    offenders = {
        str(p.relative_to(PACKAGE)): found
        for p in modules_outside_ui()
        if (found := forbidden_imports(p.read_text()))
    }
    assert offenders == {}
