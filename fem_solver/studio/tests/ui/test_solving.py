import json

import pytest
from PySide6.QtCore import QTimer

pytestmark = pytest.mark.ui

WAIT_MS = 30000


def press_run(qtbot, window):
    """Click Run and wait until the solve has ended; returns (number, state, message)."""
    with qtbot.waitSignal(window.runner.finished, timeout=WAIT_MS) as finished:
        window.workflow._run.click()
    return tuple(finished.args)


def wait_for_output(qtbot, window, lines=1):
    """Until the fake solver has printed some progress, with the event loop running."""
    qtbot.waitUntil(
        lambda: sum("fake fem: step" in line for line in window.log.lines()) >= lines,
        timeout=WAIT_MS,
    )


def use_fake_solver(monkeypatch, fake_fem, window, mode="ok"):
    monkeypatch.setenv("FEM_EXECUTABLE", str(fake_fem))
    monkeypatch.setenv("FAKE_FEM_MODE", mode)
    window.workflow.set_backend("fem")


def test_the_mock_backend_is_the_default_and_a_valid_scene_can_run(opened):
    assert opened.workflow.backend() == "mock"
    assert opened.workflow.run_enabled()
    assert opened.menu._run_action.isEnabled()
    assert opened.workflow.run_text() == "Run"


def test_nothing_runs_without_a_scene(window):
    assert not window.workflow.run_enabled()
    assert "scene" in window.workflow._run.toolTip()
    window.workflow._run.click()
    assert not window.runner.busy


def test_a_full_run_with_the_mock_backend_from_the_window(qtbot, opened):
    number, state, message = press_run(qtbot, opened)
    assert (number, state, message) == (1, "success", "mock field, not a solution")
    lines = opened.log.lines()
    assert "[run] run 1 started on mock" in lines
    assert "[run] run 1 success: mock field, not a solution" in lines
    assert any(line.startswith("mock solver:") for line in lines)
    assert opened.status.run_text() == "Run 1: success"
    assert [name for name, _ in opened.scene_dock.rows()["run"]] == ["run 1"]
    assert opened.scene_dock.rows()["run"][0][1].endswith(" s")
    assert opened.workflow.run_enabled()
    assert opened.workflow.run_text() == "Run"


def test_the_run_folder_holds_the_scene_it_was_started_with(qtbot, opened):
    press_run(qtbot, opened)
    (run,) = opened.session.runs()
    assert (run.result_dir / "solution.csv").is_file()
    assert run.state == "success"
    scene = json.loads(run.scene_path.read_text())
    assert [s["name"] for s in scene["shapes"]] == ["electrode", "glass_outer", "wall"]


def test_a_second_run_is_numbered_after_the_first(qtbot, opened):
    press_run(qtbot, opened)
    number, state, _ = press_run(qtbot, opened)
    assert (number, state) == (2, "success")
    assert [name for name, _ in opened.scene_dock.rows()["run"]] == ["run 2", "run 1"]


def test_runs_of_a_scene_outside_a_project_are_dropped_when_another_opens(qtbot, opened):
    press_run(qtbot, opened)
    folder = opened.session.runs()[0].folder
    assert folder.is_dir()
    opened.new_scene()
    assert opened.session.runs() == []
    assert not folder.exists()


def test_the_window_stays_responsive_while_the_solver_works(qtbot, opened, monkeypatch, fake_fem):
    use_fake_solver(monkeypatch, fake_fem, opened, "chatty")
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(20)
    opened.workflow._run.click()
    assert opened.runner.busy
    assert opened.workflow.run_text() == "Stop"
    assert opened.workflow.run_enabled()
    wait_for_output(qtbot, opened, lines=5)
    assert len(ticks) >= 5  # the event loop kept running while the solver printed
    assert opened.runner.busy
    with qtbot.waitSignal(opened.runner.finished, timeout=WAIT_MS) as finished:
        opened.workflow._run.click()  # Stop
    timer.stop()
    assert finished.args[1:] == ["stopped", "stopped by the user"]
    assert not opened.runner.busy
    assert opened.status.run_text() == "Run 1: stopped"
    assert opened.workflow.run_text() == "Run"


def test_edits_made_during_a_solve_do_not_reach_it(qtbot, opened, monkeypatch, fake_fem):
    use_fake_solver(monkeypatch, fake_fem, opened, "chatty")
    opened.workflow._run.click()
    wait_for_output(qtbot, opened)
    opened.properties.panel("Geometry").add_item("circle")
    assert len(opened.session.scene.shapes) == 4
    (run,) = opened.session.runs()
    saved = json.loads(run.scene_path.read_text())
    assert len(saved["shapes"]) == 3
    with qtbot.waitSignal(opened.runner.finished, timeout=WAIT_MS):
        opened.workflow._run.click()


def test_a_failed_solve_is_reported_in_the_log_and_an_error_dialog(
    qtbot, opened, monkeypatch, fake_fem, errors
):
    use_fake_solver(monkeypatch, fake_fem, opened, "fail")
    number, state, message = press_run(qtbot, opened)
    assert (number, state) == (1, "failed")
    assert "no dirichlet boundary" in message
    assert any("run 1 failed" in line for line in opened.log.lines())
    assert errors == [("Run 1 failed", message)]
    assert opened.status.run_text() == "Run 1: failed"
    assert opened.scene_dock.rows()["run"][0] == ("run 1", "failed")
    assert opened.workflow.run_enabled()


def test_the_real_solver_executable_is_a_backend_choice(qtbot, opened, monkeypatch, fake_fem):
    use_fake_solver(monkeypatch, fake_fem, opened)
    number, state, _ = press_run(qtbot, opened)
    assert (number, state) == (1, "success")
    assert any("fake fem: problem electrostatics" in line for line in opened.log.lines())


def test_run_is_unavailable_when_the_backend_cannot_run_here(opened, monkeypatch, tmp_path):
    monkeypatch.setenv("FEM_EXECUTABLE", str(tmp_path / "missing"))
    opened.workflow.set_backend("fem")
    assert not opened.workflow.run_enabled()
    assert "'fem' backend is not available" in opened.workflow._run.toolTip()
    opened.workflow.set_backend("mock")
    assert opened.workflow.run_enabled()


def test_run_is_unavailable_while_the_scene_has_errors(opened):
    opened.session.edit(
        "break",
        lambda scene: setattr(scene.boundaries[0].condition, "values", {"g": "1 +"}),
        geometry=False,
    )
    assert not opened.workflow.run_enabled()
    reason = opened.workflow._run.toolTip()
    assert reason.startswith("boundary 'inner_electrode'")
    opened.session.undo()
    assert opened.workflow.run_enabled()


def test_closing_the_window_stops_a_solve_in_progress(qtbot, opened, monkeypatch, fake_fem):
    window = opened
    use_fake_solver(monkeypatch, fake_fem, window, "chatty")
    window.workflow._run.click()
    wait_for_output(qtbot, window)
    window.close()
    assert window.runner.wait()
    assert not window.isVisible()


def test_another_scene_cannot_be_opened_during_a_solve(
    qtbot, opened, monkeypatch, fake_fem, errors
):
    use_fake_solver(monkeypatch, fake_fem, opened, "chatty")
    opened.workflow._run.click()
    wait_for_output(qtbot, opened)
    assert not opened.new_scene()
    assert errors and errors[0][0] == "New scene"
    with qtbot.waitSignal(opened.runner.finished, timeout=WAIT_MS):
        opened.workflow._run.click()
