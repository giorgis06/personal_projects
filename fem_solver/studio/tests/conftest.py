import os
import stat
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

STUDIO = Path(__file__).resolve().parents[1]
FAKE = Path(__file__).resolve().parent / "backends" / "fake_fem.py"


@pytest.fixture
def fake_fem(tmp_path_factory, monkeypatch):
    """An executable that runs fake_fem.py; set FAKE_FEM_MODE to change what it does."""
    script = tmp_path_factory.mktemp("bin") / "fem"
    script.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE}" "$@"\n')
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PYTHONPATH", str(STUDIO))
    return script
