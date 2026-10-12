import pytest
from femstudio.backends import registry
from femstudio.backends.base import SolverBackend
from femstudio.backends.executable import ExecutableBackend
from femstudio.backends.mock import MockBackend


class Dummy(SolverBackend):
    name = "dummy"
    supported_problem_types = ("heat",)

    def is_available(self):
        return False

    def solve(self, run_folder, on_log):
        raise NotImplementedError


@pytest.fixture
def clean_registry(monkeypatch):
    monkeypatch.setattr(registry, "_registered", dict(registry._registered))
    return registry


def test_builtin_backends_are_found_by_name():
    assert isinstance(registry.get("mock"), MockBackend)
    assert isinstance(registry.get("fem"), ExecutableBackend)
    assert [b.name for b in registry.available()] == ["fem", "mock"]


def test_unknown_backend_lists_what_is_registered():
    with pytest.raises(registry.UnknownBackend, match="registered: fem, mock"):
        registry.get("cuda")


def test_new_backend_is_registered_not_special_cased(clean_registry):
    clean_registry.register(Dummy())
    assert clean_registry.get("dummy").supports("heat")
    assert not clean_registry.get("dummy").supports("electrostatics")


def test_duplicate_name_is_refused(clean_registry):
    with pytest.raises(ValueError, match="already registered"):
        clean_registry.register(MockBackend())
