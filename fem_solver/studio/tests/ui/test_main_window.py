import pytest
from femstudio.ui.main_window import MainWindow

pytestmark = pytest.mark.ui


def test_window_opens(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    assert window.isVisible()
    assert window.windowTitle() == "FEM Studio"
