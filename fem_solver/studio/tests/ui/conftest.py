import copy
import os
import sys
from pathlib import Path

import pytest
from femstudio.core.project.document import open_document

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "capacitor.scene.json"
DATA = Path(__file__).resolve().parents[3] / "tests" / "data"


@pytest.fixture(scope="session")
def capacitor_document(tmp_path_factory):
    """The capacitor meshed once; tests that change the scene work on a copy."""
    return open_document(EXAMPLE, tmp_path_factory.mktemp("capacitor"))


@pytest.fixture
def document(capacitor_document):
    return copy.deepcopy(capacitor_document)


@pytest.fixture
def window(qtbot, settings):
    """A shown window, closed here rather than by qtbot.

    qtbot closes its widgets before fixtures are torn down, when a test may still have the
    unsaved-changes answer patched to "cancel": the window would then stay open and its 3D
    widget would outlive its GL context, aborting the process a few tests later.
    """
    from femstudio.ui.main_window import MainWindow

    window = MainWindow(settings)
    window.show()
    qtbot.waitExposed(window)
    yield window
    window.session._set_dirty(False)
    window.close()
    window.deleteLater()


@pytest.fixture
def opened(window):
    assert window.open_path(EXAMPLE)
    return window


@pytest.fixture
def session():
    """A Session with the capacitor open; its temporary folder goes at the end of the test."""
    from femstudio.ui.session import Session

    opened = Session()
    assert opened.open_path(EXAMPLE)
    yield opened
    opened.close()


@pytest.fixture
def errors(monkeypatch):
    """Collects what the window would show in an error dialog, instead of showing it."""
    from femstudio.ui.main_window import MainWindow

    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(
        MainWindow, "report_error", lambda self, title, text: shown.append((title, text))
    )
    return shown


def _can_import_pyvista() -> bool:
    try:
        import pyvista  # noqa: F401
    except ImportError:
        return False
    return True


if not _can_import_pyvista():  # a machine without VTK's libraries: skip, loudly
    import warnings

    warnings.warn(
        "pyvista cannot be imported here; the window tests are not collected", stacklevel=1
    )
    collect_ignore_glob = ["test_*.py", "*/test_*.py"]


@pytest.fixture(autouse=True)
def _zoom_at_one_hundred_percent():
    """The zoom factor is process-wide state; every test starts and ends at 100 %."""
    from femstudio.ui.theme import zoom

    zoom.set_current(1.0)
    yield
    zoom.set_current(1.0)


@pytest.fixture
def settings(tmp_path):
    """Settings in a temporary file, so a test never touches the real stored choice."""
    from PySide6.QtCore import QSettings

    return QSettings(str(tmp_path / "femstudio.ini"), QSettings.Format.IniFormat)


@pytest.fixture(autouse=True)
def _unsaved_changes_answer(monkeypatch):
    """A window closed with unsaved edits would block on a dialog; tests answer it themselves.

    The default is "discard"; a test that checks the question replaces `ask_unsaved`.
    """
    from femstudio.ui.main_window import MainWindow

    monkeypatch.setattr(MainWindow, "ask_unsaved", lambda self: "discard")


@pytest.fixture(autouse=True)
def _stop_solve_answer(monkeypatch):
    """A window closed during a solve would block on a dialog; the default answer is yes."""
    from femstudio.ui.main_window import MainWindow

    monkeypatch.setattr(MainWindow, "ask_stop_solve", lambda self: True)


_exit_status = 0


def pytest_sessionfinish(session, exitstatus):
    global _exit_status
    _exit_status = int(exitstatus)


@pytest.hookimpl(tryfirst=True)
def pytest_unconfigure(config):
    """End the process once the report is printed.

    After many windows VTK's own teardown aborts inside the interpreter's final garbage
    collection ("free(): invalid pointer"), turning a passing run into a core dump. Nothing is
    left to write at this point, so the process leaves without running that teardown.
    """
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_exit_status)
