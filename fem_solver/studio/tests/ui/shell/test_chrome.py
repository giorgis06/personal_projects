import pytest
from femstudio.core.scene.boundary import BoundaryCondition
from femstudio.core.scene.validation import Finding
from femstudio.ui.results_state import ResultsState
from femstudio.ui.shell.log_dock import LogDock
from femstudio.ui.shell.menu_bar import MainMenuBar
from femstudio.ui.shell.status_bar import (
    FindingsDialog,
    StatusPanel,
    collect_findings,
    summarise,
)
from femstudio.ui.shell.viewport import TAB_FOR_STEP, TABS, Viewport
from femstudio.ui.shell.workflow_bar import STEPS, WorkflowBar
from PySide6.QtWidgets import QDockWidget


def test_steps_are_in_the_planned_order():
    assert STEPS == ("Geometry", "Physics", "Mesh", "Solve", "Results")


def test_every_step_has_a_viewport_tab_that_exists():
    assert set(TAB_FOR_STEP) == set(STEPS)
    assert set(TAB_FOR_STEP.values()) <= set(TABS)
    assert TABS == ("Heatmap", "3D surface", "Mesh", "Geometry")


@pytest.mark.ui
def test_workflow_bar_selects_one_step_at_a_time(qtbot):
    bar = WorkflowBar()
    qtbot.addWidget(bar)
    assert bar.steps() == list(STEPS)
    assert bar.step() == "Geometry"
    with qtbot.waitSignal(bar.stepChanged) as signal:
        bar._buttons["Mesh"].click()
    assert signal.args == ["Mesh"]
    assert bar.step() == "Mesh"
    bar.set_step("Results")
    assert bar.step() == "Results"
    assert [b.isChecked() for b in bar._buttons.values()].count(True) == 1


@pytest.mark.ui
def test_workflow_bar_backend_selector_and_run_button(qtbot):
    bar = WorkflowBar()
    qtbot.addWidget(bar)
    bar.set_backends(["fem", "mock"])
    assert bar.backends() == ["fem", "mock"] and bar.backend() == "fem"
    with qtbot.waitSignal(bar.backendChanged) as signal:
        bar._backend.setCurrentText("mock")
    assert signal.args == ["mock"]
    bar.set_run_enabled(False, "later")
    assert not bar.run_enabled()
    bar.set_run_enabled(True)
    with qtbot.waitSignal(bar.runRequested):
        bar._run.click()


@pytest.mark.ui
def test_menu_bar_has_the_planned_menus_and_lists_every_dock(qtbot):
    menu = MainMenuBar()
    qtbot.addWidget(menu)
    assert menu.menu_titles() == ["File", "Edit", "View", "Run", "Help"]
    docks = []
    for title in ("Scene", "Properties", "Log"):
        dock = QDockWidget(title)
        qtbot.addWidget(dock)
        docks.append(dock)
    menu.set_docks(docks)
    assert menu.view_titles() == [
        "Scene",
        "Properties",
        "Log",
        "Zoom in",
        "Zoom out",
        "Reset zoom",
        "Reset layout",
    ]


@pytest.mark.ui
def test_log_dock_appends_lines_in_order(qtbot):
    log = LogDock()
    qtbot.addWidget(log)
    for line in ("[mesh] one", "[mesh] two\n", "[done]"):
        log.append_line(line)
    assert log.lines() == ["[mesh] one", "[mesh] two", "[done]"]
    log.clear()
    assert log.lines() == []


@pytest.mark.ui
def test_viewport_tabs_in_order_and_switching(qtbot):
    viewport = Viewport(ResultsState())
    qtbot.addWidget(viewport)
    assert viewport.tab_titles() == ["Heatmap", "3D surface", "Mesh", "Geometry"]
    viewport.show_tab("Mesh")
    assert viewport.current_title() == "Mesh"


def test_validation_summary_wording():
    error = Finding("error", "names", "region 'a'", "m")
    warning = Finding("warning", "no-dirichlet", "scene", "m")
    assert summarise([]) == ("Validation: 0 errors, 0 warnings", "ok")
    assert summarise([warning]) == ("Validation: 0 errors, 1 warning", "warning")
    assert summarise([warning, error, error]) == ("Validation: 2 errors, 1 warning", "error")


def test_a_clean_scene_has_no_findings(document):
    assert collect_findings(document) == []


def test_findings_combine_the_generic_and_problem_type_checks(document):
    document.scene.boundaries[1].condition = None
    document.scene.boundaries[0].condition = BoundaryCondition("periodic", {})
    rules = {f.rule for f in collect_findings(document)}
    assert rules == {"boundary-default", "boundary-kind", "no-dirichlet"}


def test_unknown_problem_type_is_a_finding_not_a_crash(document):
    document.scene.problem_type = "magnetostatics"
    findings = collect_findings(document)
    assert any(f.rule == "problem-type" for f in findings)


@pytest.mark.ui
def test_status_bar_shows_counts_and_summary(qtbot, document):
    status = StatusPanel()
    qtbot.addWidget(status)
    status.set_document(document)
    nodes, triangles = document.mesh.n_nodes, document.mesh.n_triangles
    assert status.texts() == [
        "Validation: 0 errors, 0 warnings",
        f"{nodes:,} nodes".replace(",", " "),
        f"{triangles:,} triangles".replace(",", " "),
        "h = 0.1",
    ]


@pytest.mark.ui
def test_clicking_the_summary_lists_the_findings_by_name(qtbot, document):
    document.scene.boundaries[1].condition = None
    status = StatusPanel()
    qtbot.addWidget(status)
    status.set_document(document)
    assert status.texts()[0] == "Validation: 0 errors, 1 warning"
    dialog = status.show_findings()
    qtbot.addWidget(dialog)
    assert dialog.lines() == [
        "warning: boundary 'outer_wall': has no condition, so it is insulating (neumann, g = 0)"
    ]


@pytest.mark.ui
def test_findings_dialog_says_when_there_is_nothing(qtbot):
    dialog = FindingsDialog([])
    qtbot.addWidget(dialog)
    assert dialog.lines() == ["No findings."]


@pytest.mark.ui
def test_choosing_a_step_from_code_announces_it(qtbot):
    bar = WorkflowBar()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.stepChanged) as signal:
        bar.set_step("Physics")
    assert signal.args == ["Physics"]
    assert bar.step() == "Physics"


def test_a_scene_that_cannot_be_meshed_reports_the_reason_as_a_finding(document):
    document.mesh = None
    document.mesh_error = "3 outer curve(s) are named by no boundary"
    findings = collect_findings(document)
    assert [(f.severity, f.rule) for f in findings] == [("error", "mesh")]
    assert "named by no boundary" in findings[0].message


def test_a_meshing_error_already_explained_by_validation_is_not_repeated(document):
    document.scene.regions[1].material = {}
    document.mesh = None
    document.mesh_error = "region 'air': has no material"
    rules = [f.rule for f in collect_findings(document)]
    assert "mesh" not in rules and "region-material" in rules


@pytest.mark.ui
def test_status_bar_without_a_mesh(qtbot, document):
    document.mesh = None
    document.mesh_error = "the scene has no shapes to mesh"
    status = StatusPanel()
    qtbot.addWidget(status)
    status.set_document(document)
    assert status.texts() == ["Validation: 1 error, 0 warnings", "", "", "not meshed"]
