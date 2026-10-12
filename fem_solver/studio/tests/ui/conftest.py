import copy
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
