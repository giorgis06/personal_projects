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


def _string_constants(path: Path) -> set[str]:
    """String literals in a module, leaving out the format spec of an f-string (`{x:g}`)."""
    tree = ast.parse(path.read_text())
    in_format_spec = {
        id(inner)
        for node in ast.walk(tree)
        if isinstance(node, ast.FormattedValue) and node.format_spec is not None
        for inner in ast.walk(node.format_spec)
    }
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in in_format_spec
    }


def test_problem_type_names_appear_only_in_their_own_package():
    from femstudio.physics import registry

    names = {p.name for p in registry.available()}
    offenders = {}
    for path in PACKAGE.rglob("*.py"):
        parts = path.relative_to(PACKAGE).parts
        if parts[:2] in {("physics", p) for p in names}:
            continue
        found = _string_constants(path) & names
        if found:
            offenders[str(path.relative_to(PACKAGE))] = sorted(found)
    assert offenders == {}


def test_ui_does_not_spell_out_field_or_boundary_kind_names():
    from femstudio.physics import registry

    spelled = set()
    for problem in registry.available():
        spelled |= {f.name for f in problem.material_fields + problem.source_fields}
        spelled |= {k.name for k in problem.boundary_kinds}
        spelled |= {f.name for k in problem.boundary_kinds for f in k.fields}
    offenders = {}
    for path in (PACKAGE / "ui").rglob("*.py"):
        found = _string_constants(path) & spelled
        if found:
            offenders[str(path.relative_to(PACKAGE))] = sorted(found)
    assert offenders == {}


def test_format_specs_are_not_mistaken_for_names(tmp_path):
    source = tmp_path / "m.py"
    source.write_text('x = f"{value:g}"\ny = "g"\n')
    assert _string_constants(source) == {"g"}
    source.write_text('x = f"{value:g}"\n')
    assert _string_constants(source) == set()
